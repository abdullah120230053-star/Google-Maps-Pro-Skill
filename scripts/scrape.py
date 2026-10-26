#!/usr/bin/env python3
"""Google Maps Scraper PRO: filtered, scored, multilingual business lead campaigns.

Uses only the Python standard library (no pip installs) and drives the kit's local engine.

Single keyword:
    python3 scripts/scrape.py "gyms in Miami FL" 25.7617 -80.1918 --depth 5

Auto-geocode (no coordinates needed):
    python3 scripts/scrape.py "cafes in Austin TX" --city "Austin, TX" --depth 5

Batch (one job, many keywords) from a file (one keyword per line):
    python3 scripts/scrape.py --keywords-file examples/queries.example.txt --city "Denver, CO"

Whole city past Google's ~120 results per search (3 x 3 map tiles, run one at a time, deduped on place_id):
    python3 scripts/scrape.py "plumbers in Phoenix AZ" --city "Phoenix, AZ" --grid 3

Skip the deep email pass over contact and about pages (on by default whenever emails are on):
    python3 scripts/scrape.py "gyms in Miami FL" --city "Miami, FL" --no-deep-emails

Notes:
- Required by the API: keywords, lat/lon (strings), max_time (SECONDS). This script fills them in.
- Geocoding uses OpenStreetMap Nominatim (free, no key). It allows ~1 request/sec and requires a
  descriptive User-Agent (set below). Do not loop it aggressively.
"""
import argparse, csv, functools, io, json, math, os, re, sys, time, urllib.request, urllib.parse, urllib.error
import html as html_lib
from concurrent.futures import ThreadPoolExecutor
import pro

ENV_KEYS = ("SCRAPER_BASE_URL", "SCRAPER_PORT", "SCRAPER_API_KEY")


def load_env_file():
    """Read SCRAPER_* from the kit's .env, the same file docker compose reads, so a remapped
    port needs one edit. Variables already set in the environment win over the file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, ".env")
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                k, sep, v = line.strip().partition("=")
                if sep and k in ENV_KEYS and k not in os.environ:
                    os.environ[k] = v.strip().strip("\"'")
    except OSError:
        pass


load_env_file()
BASE = os.environ.get("SCRAPER_BASE_URL") or f"http://localhost:{os.environ.get('SCRAPER_PORT') or '8080'}"
KEY = os.environ.get("SCRAPER_API_KEY", "")
# The 8 lead fields: what you use to contact and qualify a lead.
# Everything else (geo coordinates, IDs, hours, images, review blobs) is dropped by default.
LEAD = ["title", "phone", "emails", "website", "category", "address", "review_rating", "review_count"]
UA = "google-maps-scraper-kit/1.1 (https://github.com/Mahanaicoach/google-maps-scraper-kit)"


def req(method, path, body=None):
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if KEY:
        headers["X-API-Key"] = KEY
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, resp.read()


def geocode(place, with_bbox=False):
    """City/place name -> ('lat','lon') strings via Nominatim, or None.
    with_bbox=True returns ('lat','lon', [south, north, west, east]) instead."""
    q = urllib.parse.urlencode({"format": "json", "limit": 1, "q": place})
    url = f"https://nominatim.openstreetmap.org/search?{q}"
    r = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            hits = json.loads(resp.read())
        time.sleep(1)  # respect Nominatim's ~1 req/sec policy
        if hits:
            ll = (str(hits[0]["lat"]), str(hits[0]["lon"]))
            return ll + (hits[0].get("boundingbox"),) if with_bbox else ll
    except Exception as e:
        print(f"  (geocoding failed: {e})", file=sys.stderr)
    return None


def grid_cells(bbox, n):
    """Split a Nominatim bbox [south, north, west, east] into n x n cells -> [{lat, lon, radius, zoom}].
    radius (m) = 1.15 x half the cell diagonal (equirectangular), at least 1000.
    zoom = the Maps zoom whose ~1000px viewport is about as wide as the cell (11..17), so each
    search is launched looking at its own tile instead of a city-wide or block-wide view."""
    s, nn, w, e = (float(x) for x in bbox)
    dlat, dlon = (nn - s) / n, (e - w) / n
    m_per_deg = 6371000 * math.pi / 180
    cells = []
    for i in range(n):
        for j in range(n):
            lat, lon = s + (i + 0.5) * dlat, w + (j + 0.5) * dlon
            cos = math.cos(math.radians(lat))
            width = max(1.0, dlon * m_per_deg * cos)
            diag = math.hypot(dlat * m_per_deg, width)
            zoom = round(math.log2(156543.03 * cos * 1000 / width))  # 156543 m/px at zoom 0
            cells.append({"lat": f"{lat:.6f}", "lon": f"{lon:.6f}",
                          "radius": max(1000, math.ceil(1.15 * diag / 2)),
                          "zoom": min(17, max(11, zoom))})
    return cells


def in_bbox(row, bbox, margin=0.10):
    """True if the row's latitude/longitude sit inside bbox [south, north, west, east] grown by
    `margin` of its size on each side. Rows with no usable coordinates are kept (True)."""
    try:
        lat, lon = float(row.get("latitude")), float(row.get("longitude"))
    except (TypeError, ValueError):
        return True
    s, n, w, e = (float(x) for x in bbox)
    my, mx = (n - s) * margin, (e - w) * margin
    return s - my <= lat <= n + my and w - mx <= lon <= e + mx


def dedupe(rows):
    """Keep the first row per place_id, else cid, else link, else title+address."""
    seen, out = {}, []
    for r in rows:
        key = next((f"{k}:{r[k]}" for k in ("place_id", "cid", "link") if r.get(k)),
                   f"ta:{r.get('title', '')}|{r.get('address', '')}")
        if key not in seen:
            seen[key] = r
            out.append(r)
        else:
            first = seen[key]
            for field in ("_cities", "_languages"):
                if field in r:
                    first[field] = list(dict.fromkeys(first.get(field, []) + r[field]))
    return out


class JobError(RuntimeError):
    def __init__(self, message, job_id="", active_unknown=False):
        super().__init__(message)
        self.job_id = job_id
        self.active_unknown = active_unknown


def run_job(body):
    """Create one engine job, poll it, download it -> (job_id, raw CSV rows). Raises RuntimeError."""
    try:
        _, raw = req("POST", "/api/v1/jobs", body)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"✗ Create failed: HTTP {e.code} — {e.read().decode()[:200]}")
    job_id = json.loads(raw).get("id")
    if not job_id:
        raise RuntimeError("✗ No job id returned.")
    print(f"  job id: {job_id}")

    print("▶ Polling…")
    status = None
    deadline = time.monotonic() + body.get("max_time", 600) + 120
    i = 0
    while time.monotonic() < deadline:
        i += 1
        try:
            _, raw = req("GET", f"/api/v1/jobs/{job_id}")
            status = json.loads(raw).get("Status")
        except (OSError, ValueError) as error:
            raise JobError("Polling failed; job may still be running: " + str(error), job_id, active_unknown=True) from error
        print(f"\r  status: {str(status):<10} (attempt {i})", end="", flush=True)
        if status == "ok":
            print(); break
        if status == "failed":
            raise JobError("\n✗ Job failed. Check the engine logs; repeated failures may indicate rate limiting.", job_id)
        time.sleep(8)
    else:
        raise JobError("Polling timed out; job may still be running.", job_id, active_unknown=True)

    try:
        _, raw = req("GET", f"/api/v1/jobs/{job_id}/download")
        return job_id, list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig", "replace"))))
    except (OSError, ValueError) as error:
        raise JobError("Download failed: " + str(error), job_id) from error


def collect_keywords(a):
    kws = []
    if a.keyword:
        kws.append(a.keyword)
    kws.extend(a.also or [])
    if a.keywords_file:
        with open(a.keywords_file, encoding="utf-8-sig") as f:
            kws.extend(line.strip() for line in f if line.strip() and not line.lstrip().startswith("#"))
    # de-dupe, keep order
    seen, out = set(), []
    for k in kws:
        if k not in seen:
            seen.add(k); out.append(k)
    return out


# Social links are discovered on business websites; social platforms are not crawled.
URL_RE = re.compile(r"(?:https?:)?//[^\s\"'<>\\]+", re.I)
_SKIP_HANDLE = {"", "home", "pages", "people", "help", "about", "policies", "policy",
                "legal", "tos", "privacy", "settings", "sharer", "tr", "profile.php",
                "plugins", "dialog", "intent", "login", "share.php", "permalink.php",
                "p", "reel", "reels", "explore", "stories", "tv", "watch", "events",
                "groups", "marketplace", "gaming", "photo", "hashtag", "search", "intent",
                "share", "login.php", "signup", "accounts", "i", "status", "shorts", "watch"}


def is_social_site(url):
    try:
        host = (urllib.parse.urlsplit(url if "://" in url else "https://" + url).hostname or "").lower()
    except ValueError:
        return False
    host = re.sub(r"^(?:www\.|m\.|web\.)", "", host)
    return host in {"instagram.com", "facebook.com", "linkedin.com", "youtube.com", "tiktok.com",
                    "x.com", "twitter.com", "wa.me", "api.whatsapp.com"} or bool(re.fullmatch(r"[a-z]{2,3}\.linkedin\.com", host))


@functools.lru_cache(maxsize=512)
def _fetch_page(url, timeout=8):
    if not url:
        return {"html": "", "url": "", "status": None, "state": "missing"}
    if is_social_site(url):
        return {"html": "", "url": url, "status": None, "state": "social_profile"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urllib.parse.urlsplit(url)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password
        port = parsed.port
    except ValueError:
        valid = False
    if not valid:
        return {"html": "", "url": url, "status": None, "state": "invalid_url"}
    try:
        host = parsed.hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return {"html": "", "url": url, "status": None, "state": "invalid_url"}
    if ":" in host:
        host = "[" + host + "]"
    netloc = host + (":" + str(port) if port else "")
    url = urllib.parse.urlunsplit((parsed.scheme, netloc, urllib.parse.quote(parsed.path, safe="/%:@"),
                                   urllib.parse.quote(parsed.query, safe="=&%+/:?@"), ""))
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; " + UA + ")", "Accept": "text/html"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            ctype = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(400_000)
            try:
                text = raw.decode(charset, "replace")
            except LookupError:
                text = raw.decode("utf-8", "replace")
            return {"html": text if ctype in {"text/html", "application/xhtml+xml"} else "",
                    "url": response.geturl(), "status": response.status,
                    "state": "reachable" if ctype in {"text/html", "application/xhtml+xml"} else "non_html"}
    except urllib.error.HTTPError as error:
        result = {"html": "", "url": error.geturl(), "status": error.code,
                  "state": "blocked" if error.code in {401, 403, 429} else "http_error"}
        error.close()
        return result
    except (OSError, ValueError, urllib.error.URLError):
        return {"html": "", "url": url, "status": None, "state": "unreachable"}

def _fetch_html(url, timeout=10):
    return _fetch_page(url, timeout)["html"]

def _find_socials(html):
    out = dict.fromkeys(pro.SOCIAL_FIELDS, "")
    text = html_lib.unescape((html or "").replace("\\/", "/"))
    for raw in URL_RE.findall(text):
        url = ("https:" + raw if raw.startswith("//") else raw).rstrip(".,);]")
        try:
            parsed = urllib.parse.urlsplit(url)
            host = (parsed.hostname or "").lower()
        except ValueError:
            continue
        host = re.sub(r"^(?:www\.|m\.|web\.)", "", host)
        parts = [p for p in parsed.path.split("/") if p]
        if not parts or parsed.username or parsed.password:
            continue
        handle, platform, path = parts[0], None, None
        if host == "instagram.com" and handle.casefold() not in _SKIP_HANDLE:
            platform, path = "instagram", "/" + handle
        elif host == "facebook.com":
            if handle == "profile.php":
                ident = urllib.parse.parse_qs(parsed.query).get("id", [""])[0]
                if ident.isdigit():
                    platform, path = "facebook", "/profile.php?id=" + ident
            elif handle == "pages" and len(parts) >= 3 and parts[2].isdigit():
                platform, path = "facebook", "/" + "/".join(parts[:3])
            elif handle.casefold() not in _SKIP_HANDLE:
                platform, path = "facebook", "/" + handle
        elif (host == "linkedin.com" or re.fullmatch(r"[a-z]{2,3}\.linkedin\.com", host)) and len(parts) >= 2 and handle in {"company", "in", "school"}:
            platform, path, host = "linkedin", "/" + "/".join(parts[:2]), "linkedin.com"
        elif host == "youtube.com" and (handle.startswith("@") or handle in {"channel", "c", "user"} and len(parts) >= 2):
            platform, path = "youtube", "/" + (handle if handle.startswith("@") else "/".join(parts[:2]))
        elif host == "tiktok.com" and handle.startswith("@"):
            platform, path = "tiktok", "/" + handle
        elif host in {"x.com", "twitter.com"} and handle.casefold() not in _SKIP_HANDLE:
            platform, path, host = "x", "/" + handle, "x.com"
        elif host in {"wa.me", "api.whatsapp.com"}:
            phone = handle if host == "wa.me" else urllib.parse.parse_qs(parsed.query).get("phone", [""])[0]
            phone = re.sub(r"[+\s()-]", "", phone)
            if phone.isdigit() and 7 <= len(phone) <= 15:
                platform, path, host = "whatsapp", "/" + phone, "wa.me"
        if platform and not out[platform]:
            out[platform] = "https://" + host + path
    return out

def enrich_socials(results, workers=8):
    """Add published social profile URLs plus the page on which each URL was found."""
    for r in results:
        for field in pro.SOCIAL_FIELDS:
            r.setdefault(field, "")
            r.setdefault(field + "_source", "")
    todo = [r for r in results if r.get("website")]
    done = 0
    def work(r):
        site = r["website"]
        direct = _find_socials(site) if is_social_site(site) else {}
        page = _fetch_page(site) if not any(direct.values()) else {"html": "", "url": site}
        sources = [(site, direct), (page["url"], _find_socials(page["html"]))]
        # Contact links can carry profiles omitted from the homepage footer.
        if page["html"] and not any(direct.values()) and not any(sources[1][1].values()):
            for url in contact_links(page["html"], page["url"])[:1]:
                extra = _fetch_page(url)
                sources.append((extra["url"], _find_socials(extra["html"])))
        for source, found in sources:
            for field, url in found.items():
                if url and not r[field]:
                    r[field], r[field + "_source"] = url, source
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for _ in ex.map(work, todo):
            done += 1
            print(f"\r  socials: {done}/{len(todo)} sites checked", end="", flush=True)
    print()


# ── Deep email pass: contact/about pages for rows the engine left without an email ──
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAILTO_RE = re.compile(r"mailto:([^\"'>\s?]+)", re.I)
HREF_RE = re.compile(r"<a\s[^>]*?href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
CONTACT_RE = re.compile(r"contact|about|تواصل|اتصل|اتصال|من\s+نحن|عن[\s_-]*(?:الشركة|العيادة|المركز|المؤسسة)", re.I)
_JUNK_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")
_JUNK_DOMAIN = ("example", "sentry", "wixpress", "wix.com", "godaddy", "squarespace", "wordpress",
                "domain.com", "email.com", "yourdomain", "schema.org", "w3.org", "sentry.io")
_JUNK_LOCAL = {"name", "email", "user", "you", "someone"}

def _host(url):
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    h = (urllib.parse.urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h

def extract_emails(html, site_host):
    """Emails from mailto: links and plain text, junk dropped, site-domain first, max 3."""
    site = _host(site_host or "")
    found = []
    decoded = html_lib.unescape(html or "")
    for e in MAILTO_RE.findall(decoded) + EMAIL_RE.findall(decoded):
        e = urllib.parse.unquote(e).strip().lower()
        local, _, dom = e.rpartition("@")
        if (not EMAIL_RE.fullmatch(e) or e.endswith(_JUNK_EXT) or local in _JUNK_LOCAL
                or any(j in dom for j in _JUNK_DOMAIN) or e in found):
            continue
        found.append(e)
    on_site = lambda e: site and (e.endswith("@" + site) or e.endswith("." + site))
    return sorted(found, key=lambda e: not on_site(e))[:3]

def contact_links(html, base_url):
    """Up to 3 same-site contact/about URLs: discovered links first, then fixed fallbacks."""
    if not base_url.startswith(("http://", "https://")):
        base_url = "http://" + base_url
    host, out = _host(base_url), []
    for href, text in HREF_RE.findall(html or ""):
        if not CONTACT_RE.search(urllib.parse.unquote(href) + " " + text):
            continue
        url = urllib.parse.urldefrag(urllib.parse.urljoin(base_url, html_lib.unescape(href.strip())))[0]
        if url.startswith(("http://", "https://")) and _host(url) == host and url not in out:
            out.append(url)
    for path in ("/contact", "/contact-us", "/about", "/about-us"):
        url = urllib.parse.urljoin(base_url, path)
        if len(out) < 3 and url not in out:
            out.append(url)
    return out[:3]

def enrich_emails(results, workers=8):
    """Fill empty `emails` from the homepage, then up to 3 contact/about pages. Zero LLM tokens."""
    todo = [r for r in results if r.get("website") and not r.get("emails")]
    done = 0
    def work(r):
        site = r["website"]
        page = _fetch_page(site)
        home, site = page["html"], page["url"]
        found = extract_emails(home, site)
        if home and not found:
            pages = "".join(_fetch_html(u, timeout=8) for u in contact_links(home, site))
            found = extract_emails(pages, site)
        r["emails"] = ", ".join(found)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for _ in ex.map(work, todo):
            done += 1
            print(f"\r  emails: {done}/{len(todo)} sites checked", end="", flush=True)
    print()


def check_websites(results, workers=8):
    """Observe the homepage only; never infer permanent failure or website quality."""
    def work(row):
        site = row.get("website") or ""
        page = _fetch_page(site)
        state = page["state"]
        contact = ""
        for href, text in HREF_RE.findall(page["html"]):
            candidate = urllib.parse.urljoin(page["url"], html_lib.unescape(href))
            if CONTACT_RE.search(urllib.parse.unquote(href) + " " + text) and candidate.startswith(("https://", "http://")) and _host(candidate) == _host(page["url"]):
                contact = candidate
                break
        https = urllib.parse.urlsplit(page["url"]).scheme == "https" if state in {"reachable", "non_html"} else ""
        opportunities = []
        if state == "missing":
            opportunities.append("no website listed")
        elif state == "social_profile":
            opportunities.append("listed website is a social profile")
        elif state in {"unreachable", "http_error", "blocked", "invalid_url"}:
            opportunities.append("request needs manual review: " + state)
        if https is False:
            opportunities.append("final page uses HTTP")
        if state == "reachable" and not contact:
            opportunities.append("no contact/about link detected on homepage")
        row.update(website_status=state, website_http_status=page["status"] or "",
                   website_final_url=page["url"], website_https=https,
                   website_contact_link=contact, website_opportunities="; ".join(opportunities))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for i, _ in enumerate(executor.map(work, results), 1):
            print(f"\r  websites: {i}/{len(results)} checked", end="", flush=True)
    print()


def main(argv=None):
    import campaign
    return campaign.run(argparse.Namespace(**globals()), argv)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    main()

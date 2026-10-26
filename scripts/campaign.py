"""CLI orchestration. The engine namespace supplies HTTP, geocoding and enrichment."""
import argparse
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pro


def parser():
    ap = argparse.ArgumentParser(description="Google Maps Scraper PRO: targeted, scored campaigns and Excel exports.")
    ap.add_argument("keyword", nargs="?", help='search term; use "dentists in {city}" for multiple cities')
    ap.add_argument("lat", nargs="?")
    ap.add_argument("lon", nargs="?")
    ap.add_argument("--keyword", dest="also", action="append", help="additional search term (repeatable)")
    ap.add_argument("--keywords-file", help="UTF-8 keyword file, one term per line")
    ap.add_argument("--campaign", help="saved JSON campaign; explicit CLI options override its settings")
    ap.add_argument("--city", action="append", help="city to geocode; repeat for multiple cities")
    ap.add_argument("--lang", action="append", help="engine language (en/ar); repeat to search in both")
    ap.add_argument("--depth", type=int, default=5)
    ap.add_argument("--grid", type=int, help="N x N tiles per city (1..10)")
    ap.add_argument("--max-time", type=int, default=600, help="seconds per engine job")
    for positive, negative, dest, default, help_text in (
            ("--email", "--no-email", "email", True, "extract published business emails"),
            ("--deep-emails", "--no-deep-emails", "deep_emails", True, "check multilingual contact/about pages"),
            ("--socials", "--no-socials", "socials", True, "include social profile links (on by default)"),
            ("--website-check", "--no-website-check", "website_check", False, "check homepage reachability, HTTPS and contact links")):
        group = ap.add_mutually_exclusive_group()
        group.add_argument(positive, dest=dest, action="store_true", help=help_text)
        group.add_argument(negative, dest=dest, action="store_false")
        ap.set_defaults(**{dest: default})
    ap.add_argument("--rtl", action="store_true", help="right-to-left Excel sheets (automatic when ar is selected)")
    ap.add_argument("--out", help=".csv, .json or .xlsx output path")
    formats = ap.add_mutually_exclusive_group()
    formats.add_argument("--format", choices=["csv", "json", "xlsx"])
    formats.add_argument("--json", dest="format", action="store_const", const="json")
    formats.add_argument("--xlsx", dest="format", action="store_const", const="xlsx")
    projection = ap.add_mutually_exclusive_group()
    projection.add_argument("--full", action="store_true", help="all raw and PRO columns")
    projection.add_argument("--fields", help="exact comma-separated output columns; enrichment still uses full rows")
    ap.add_argument("--report", help="JSON report path; default: <output stem>.report.json")
    for name, typ in (("min-rating", float), ("max-rating", float), ("min-reviews", int), ("max-reviews", int), ("min-score", float)):
        ap.add_argument("--" + name, type=typ)
    ap.add_argument("--category", action="append", help="include category substring (repeatable, OR)")
    ap.add_argument("--exclude-category", action="append", help="exclude category substring (repeatable)")
    websites = ap.add_mutually_exclusive_group()
    websites.add_argument("--has-website", action="store_true")
    websites.add_argument("--no-website", action="store_true")
    ap.add_argument("--has-email", action="store_true")
    ap.add_argument("--has-phone", action="store_true")
    ap.add_argument("--has-socials", action="store_true")
    ap.add_argument("--business-status", action="append", help="exact listing status (repeatable); unknown status is excluded")
    ap.add_argument("--score-profile", choices=list(pro.PROFILES), default="balanced")
    ap.add_argument("--score-config", help="JSON scoring overrides; see examples/scoring.example.json")
    return ap


def parse_args(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = parser()
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--campaign")
    known, _ = pre.parse_known_args(argv)
    cfg = pro.load_campaign(known.campaign) if known.campaign else {}
    defaults = dict(cfg.get("options", {}), **cfg.get("filters", {}))
    if "languages" in cfg:
        defaults["lang"] = cfg["languages"]
    defaults["score_profile"] = cfg.get("scoring", {}).get("profile", "balanced")
    # Repeatable options supplied on CLI replace their saved lists rather than append to them.
    supplied = {token.split("=", 1)[0] for token in argv if token.startswith("--")}
    for dest in ("lang", "category", "exclude_category", "business_status"):
        if "--" + dest.replace("_", "-") in supplied:
            defaults.pop(dest, None)
    for positive, negative, dest in (("--socials", "--no-socials", "socials"),
                                    ("--email", "--no-email", "email"),
                                    ("--deep-emails", "--no-deep-emails", "deep_emails"),
                                    ("--website-check", "--no-website-check", "website_check")):
        if supplied & {positive, negative}:
            defaults.pop(dest, None)
    if supplied & {"--has-website", "--no-website"}:
        defaults.pop("has_website", None)
        defaults.pop("no_website", None)
    ap.set_defaults(**defaults)
    a = ap.parse_args(argv)
    for key in pro.FILTER_KEYS | pro.OPTION_KEYS:
        value = getattr(a, key, None)
        if key in {"category", "exclude_category", "business_status"}:
            if value is not None:
                setattr(a, key, pro.string_list(value, key))
        elif key in {"depth", "max_time", "grid", "min_reviews", "max_reviews"}:
            if value is not None and (type(value) is not int or value < (1 if key in {"depth", "max_time", "grid"} else 0)):
                ap.error(key + " must be a positive integer (review counts may be zero)")
        elif key in {"min_rating", "max_rating", "min_score"}:
            top = 100 if key == "min_score" else 5
            if value is not None and (type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= top):
                ap.error(f"{key} must be between 0 and {top}")
        elif value is not None and type(value) is not bool:
            ap.error(key + " must be true or false")
    for low, high in (("min_rating", "max_rating"), ("min_reviews", "max_reviews")):
        if getattr(a, low) is not None and getattr(a, high) is not None and getattr(a, low) > getattr(a, high):
            ap.error(low + " cannot exceed " + high)
    if a.grid is not None and a.grid > 10:
        ap.error("--grid must be between 1 and 10")
    if a.has_website and a.no_website:
        ap.error("has_website and no_website are mutually exclusive")
    if a.has_socials and not a.socials:
        ap.error("--has-socials requires social discovery; remove --no-socials")
    if a.has_email and not a.email:
        ap.error("--has-email requires email extraction; remove --no-email")
    a.lang = pro.string_list(a.lang or ["en"], "languages")
    if any(lang not in {"en", "ar"} for lang in a.lang):
        ap.error("Supported languages: en, ar")
    if a.fields is not None and not any(f.strip() for f in a.fields.split(",")):
        ap.error("--fields must contain at least one column")
    if a.score_profile not in pro.PROFILES:
        ap.error("Unknown scoring profile")
    overrides = {k: v for k, v in cfg.get("scoring", {}).items() if k != "profile"}
    if a.score_config:
        external = pro.read_json(a.score_config)
        if not isinstance(external, dict):
            ap.error("--score-config must contain an object")
        overrides = dict(overrides, **external)
    rules = pro.scoring_rules(a.score_profile, overrides)
    if "--no-website-check" not in supplied and any(rules["weights"].get(s, 0) for s in {"website_unreachable", "no_https", "no_contact_link"}):
        if cfg.get("options", {}).get("website_check") is not False or "--website-check" in supplied:
            a.website_check = True
    if (a.lat is None) != (a.lon is None):
        ap.error("Provide both lat and lon")
    if a.lat is not None and (pro.number(a.lat) is None or pro.number(a.lon) is None or not -90 <= pro.number(a.lat) <= 90 or not -180 <= pro.number(a.lon) <= 180):
        ap.error("Coordinates must be valid latitude/longitude")
    targets = pro.string_list(a.city, "cities") if a.city else cfg.get("cities", [])
    targets = [dict(name=c) if isinstance(c, str) else dict(c) for c in targets]
    if "--grid" in supplied:
        for city in targets:
            city["grid"] = a.grid
    if len(targets) > 1 and a.lat is not None:
        ap.error("Positional coordinates apply to one city only; put per-city coordinates in a campaign")
    if a.grid and not targets:
        ap.error("--grid needs --city (or campaign cities)")
    if not targets:
        targets = [{"name": "", "lat": a.lat, "lon": a.lon}]
    elif a.lat is not None:
        targets[0].update(lat=a.lat, lon=a.lon)
    suffix = Path(a.out).suffix.lower().lstrip(".") if a.out else None
    if suffix and suffix not in {"csv", "json", "xlsx"}:
        ap.error("--out must end in .csv, .json or .xlsx")
    if a.format and suffix and suffix != a.format:
        ap.error("Output extension conflicts with requested format")
    a.format = a.format or suffix or "csv"
    return a, cfg, targets, rules


def localized_keywords(terms, city, language, multiple):
    name = city.get("names", {}).get(language, city["name"])
    if any(token not in {"{city}", "{lang}"} for term in terms for token in re.findall(r"\{[^}]*\}", term)):
        raise ValueError("Supported keyword placeholders: {city}, {lang}")
    if multiple and any("{city}" not in term for term in terms):
        raise ValueError('Multi-city keywords need {city}, e.g. "dentists in {city}"')
    if not name and any("{city}" in term for term in terms):
        raise ValueError("A {city} keyword needs --city or campaign cities")
    return list(dict.fromkeys(term.replace("{city}", name).replace("{lang}", language) for term in terms))


def collect(engine, a, cfg, targets):
    terms = engine.collect_keywords(a)
    if not terms:
        terms = cfg.get("keywords", [])
    variants = cfg.get("keywords_by_language", {})
    if not terms and not all(variants.get(lang) for lang in a.lang):
        raise ValueError("No keywords. Pass a keyword, --keywords-file, or campaign keywords")
    # Validate all localized queries before network access.
    for city in targets:
        for lang in a.lang:
            localized_keywords(variants.get(lang, terms), city, lang, len(targets) > 1)
    return terms, variants


def run(engine, argv=None):
    try:
        a, cfg, targets, rules = parse_args(argv)
        terms, variants = collect(engine, a, cfg, targets)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser().error(str(error))
    started = datetime.now(timezone.utc)
    clock = time.monotonic()
    out = a.out or f"results-{started.strftime('%Y%m%d-%H%M%S-%f')}.{a.format}"
    report_path = a.report or str(Path(out).with_suffix(".report.json"))
    if Path(out).resolve() == Path(report_path).resolve():
        parser().error("Results and report need different paths")
    settings = {"keywords": terms, "keywords_by_language": variants, "cities": targets,
                "languages": a.lang, "depth": a.depth, "grid": a.grid, "max_time": a.max_time,
                "socials": a.socials, "emails": a.email, "deep_emails": a.deep_emails,
                "website_check": a.website_check, "score_profile": a.score_profile,
                "scoring": rules, "filters": {key: getattr(a, key) for key in sorted(pro.FILTER_KEYS)},
                "fields": a.fields, "full": a.full}
    jobs, locations, all_rows = [], [], []
    stop = False
    planned = sum((city.get("grid", a.grid) or 1) ** 2 * len(a.lang) for city in targets)
    if planned > 1 or a.depth >= 15 or len(terms) >= 10:
        print(f"Heads-up: {planned} sequential jobs planned. Large/repeated runs can trigger temporary IP rate limits; consider proxies.")
    print(f"Campaign: {cfg.get('name', 'Google Maps PRO')} | languages: {', '.join(a.lang)} | socials: {a.socials}")
    try:
        engine.req("GET", "/api/v1/jobs")
    except Exception as error:
        sys.exit(f"Scraper not reachable; run 'docker compose up -d'. ({error})")
    for city in targets:
        name = city["name"] or "explicit coordinates / first keyword"
        grid = city.get("grid", a.grid)
        print(f"City: {name}")
        location = {"city": name, "raw_rows": 0, "unique_rows": 0, "duplicates_removed": 0,
                    "outside_bbox": 0, "exported_rows": 0}
        locations.append(location)
        bbox = None
        try:
            lat, lon = city.get("lat"), city.get("lon")
            if grid:
                geo = engine.geocode(city["name"], with_bbox=True)
                if not geo or not geo[2]:
                    raise ValueError("Could not resolve city bounding box")
                lat, lon, bbox = geo
                cells = engine.grid_cells(bbox, grid)
            else:
                if lat is None or lon is None:
                    coords = engine.geocode(city["name"] or variants.get(a.lang[0], terms)[0])
                    if not coords:
                        raise ValueError("Could not geocode city; use clearer name or coordinates")
                    lat, lon = coords
                cells = [{"lat": str(lat), "lon": str(lon), "radius": city.get("radius", 10000), "zoom": city.get("zoom", 15)}]
        except (ValueError, OSError) as error:
            location["error"] = str(error)
            print("  city skipped: " + str(error))
            continue
        city_rows = []
        for lang in a.lang:
            keywords = localized_keywords(variants.get(lang, terms), city, lang, len(targets) > 1)
            for i, cell in enumerate(cells, 1):
                entry = {"city": name, "language": lang, "cell": i, "job_id": "", "status": "failed", "rows": 0, "error": ""}
                jobs.append(entry)
                body = dict(name=cfg.get("name", "scrape-pro"), keywords=keywords, lang=lang,
                            fast_mode=False, depth=a.depth, email=a.email, max_time=a.max_time, **cell)
                print(f"  {lang} cell {i}/{len(cells)}: {', '.join(keywords)}")
                try:
                    job_id, rows = engine.run_job(body)
                    entry.update(job_id=job_id, status="ok", rows=len(rows))
                except Exception as error:
                    entry.update(error=str(error).strip(), job_id=getattr(error, "job_id", ""))
                    print(f"  cell {i}/{len(cells)} skipped: {entry['error']}")
                    if getattr(error, "active_unknown", False):
                        stop = True
                        print("Stopping new jobs because the last job may still be running. Check the engine before retrying.")
                        break
                    continue
                for row in rows:
                    row["_cities"], row["_languages"] = [name], [lang]
                location["raw_rows"] += len(rows)
                city_rows = engine.dedupe(city_rows + rows)
                print(f"  cell {i}/{len(cells)}: {len(rows)} rows, {len(city_rows)} unique so far")
            if stop:
                break
        location["duplicates_removed"] = location["raw_rows"] - len(city_rows)
        if bbox:
            kept = [row for row in city_rows if engine.in_bbox(row, bbox)]
            location["outside_bbox"] = len(city_rows) - len(kept)
            print(f"  dropped {location['outside_bbox']} rows outside the city box")
            city_rows = kept
        location["unique_rows"] = len(city_rows)
        all_rows.extend(city_rows)
        if stop:
            break
    before_global = len(all_rows)
    rows = engine.dedupe(all_rows)
    for row in rows:
        row["campaign_cities"] = "; ".join(row["_cities"])
        row["search_languages"] = "; ".join(row["_languages"])
    engine_emails = sum(pro.present(row.get("emails")) for row in rows)
    if rows and a.email and a.deep_emails:
        print("Deep email pass: English/Arabic contact pages")
        engine.enrich_emails(rows)
    if rows and a.socials:
        print("Finding published social profile links")
        engine.enrich_socials(rows)
    if rows and a.website_check:
        print("Checking business homepages")
        engine.check_websites(rows)
    for row in rows:
        pro.score_lead(row, rules)
    exclusions = Counter()
    exported = []
    for row in rows:
        reason = pro.filter_reason(row, settings["filters"])
        if reason:
            exclusions[reason] += 1
        else:
            exported.append(row)
    exported.sort(key=lambda row: -row["lead_score"])
    for location in locations:
        location["exported_rows"] = sum(location["city"] in row["_cities"] for row in exported)
    successful = sum(job["status"] == "ok" for job in jobs)
    failed = len(jobs) - successful
    failures = failed + sum("error" in loc for loc in locations)
    status = "failed" if not successful else "partial" if failures else "complete"
    report = {"schema_version": 1, "name": cfg.get("name", "Google Maps PRO"), "status": status,
              "started_at": started.isoformat(), "finished_at": datetime.now(timezone.utc).isoformat(),
              "elapsed_seconds": round(time.monotonic() - clock, 2), "settings": settings,
              "totals": {"jobs_planned": planned, "jobs_attempted": len(jobs), "jobs_succeeded": successful,
                         "jobs_not_started": planned - len(jobs),
                         "jobs_failed": failed, "locations_failed": sum("error" in loc for loc in locations),
                         "raw_rows": sum(loc["raw_rows"] for loc in locations),
                         "duplicates_removed": sum(loc["duplicates_removed"] for loc in locations) + before_global - len(rows),
                         "outside_bbox": sum(loc["outside_bbox"] for loc in locations),
                         "unique_collected": len(rows), "filtered_out": len(rows) - len(exported),
                         "exported_rows": len(exported), "emails_added": sum(pro.present(r.get("emails")) for r in rows) - engine_emails},
              "collected_coverage": pro.coverage(rows), "exported_coverage": pro.coverage(exported),
              "filter_exclusions": dict(exclusions), "locations": locations, "jobs": jobs}
    fields = list(engine.LEAD) + pro.PRO_FIELDS
    if a.socials:
        fields += pro.SOCIAL_FIELDS + [field + "_source" for field in pro.SOCIAL_FIELDS]
    if a.website_check:
        fields += pro.WEBSITE_FIELDS
    if a.full:
        fields = list(dict.fromkeys(fields + [key for row in rows for key in row if not key.startswith("_")]))
    elif a.fields:
        fields = list(dict.fromkeys(field.strip() for field in a.fields.split(",") if field.strip()))
    results = [{key: row.get(key, "") for key in fields} for row in exported]
    pro.ensure_parent(report_path)
    with open(report_path, "w", encoding="utf-8") as target:
        json.dump(report, target, indent=2, ensure_ascii=False)
    pro.write_results(out, results, fields, a.format, report, a.rtl or "ar" in a.lang)
    print(f"{status.upper()}: {len(rows)} unique collected; {len(exported)} exported; {len(rows) - len(exported)} filtered; {failed} failed jobs.")
    print(f"Emails: {report['exported_coverage']['email']['percent']}% | socials: {report['exported_coverage']['socials']['percent']}% | {report['elapsed_seconds']} seconds")
    print(f"Saved: {out}\nReport: {report_path}")
    for row in results[:5]:
        print(f"  {row.get('title', '')} | score {row.get('lead_score', '')} | {row.get('instagram', '')}")
    if status != "complete":
        raise SystemExit(2 if status == "partial" else 1)
    return report

"""Dependency-free targeting, scoring, campaign reports and Excel export helpers."""
import csv
import json
import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SOCIAL_FIELDS = ["instagram", "facebook", "linkedin", "youtube", "tiktok", "x", "whatsapp"]
WEBSITE_FIELDS = ["website_status", "website_http_status", "website_final_url",
                  "website_https", "website_contact_link", "website_opportunities"]
PRO_FIELDS = ["campaign_cities", "search_languages", "lead_score", "score_reasons"]
FILTER_KEYS = {"min_rating", "max_rating", "min_reviews", "max_reviews", "category",
               "exclude_category", "has_website", "no_website", "has_email", "has_phone",
               "has_socials", "business_status", "min_score"}
OPTION_KEYS = {"depth", "grid", "max_time", "socials", "email", "deep_emails",
               "website_check", "rtl"}
SIGNALS = {"phone", "email", "website", "missing_website", "socials", "rating", "reviews",
           "website_unreachable", "no_https", "no_contact_link"}
PROFILES = {
    "balanced": {"phone": 20, "email": 25, "website": 15, "socials": 10,
                 "rating": 15, "reviews": 15},
    "website-services": {"phone": 20, "email": 10, "missing_website": 35,
                          "website_unreachable": 25, "no_https": 10,
                          "no_contact_link": 10, "reviews": 15, "rating": 5},
}
LABELS = {"phone": "phone available", "email": "email available", "website": "website listed",
          "missing_website": "no website listed", "socials": "social profile available",
          "rating": "rating threshold met", "reviews": "review threshold met",
          "website_unreachable": "website could not be reached in this check",
          "no_https": "final page uses HTTP", "no_contact_link": "no contact link detected on homepage"}


def number(value):
    """Read machine numbers and Arabic digits; missing/invalid stays unknown."""
    try:
        n = float(str(value).strip().replace("٬", "").replace(",", "").replace("٫", "."))
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def present(value):
    return bool(str(value or "").strip())


def has_social(row):
    return any(present(row.get(f)) for f in SOCIAL_FIELDS)


def status_key(value):
    text = str(value or "").strip().casefold().replace("_", " ")
    aliases = {"open": "operational", "مفتوح": "operational", "مفتوح الآن": "operational",
               "مغلق نهائيًا": "permanently closed", "مغلق نهائيا": "permanently closed",
               "مغلق مؤقتًا": "temporarily closed", "مغلق مؤقتا": "temporarily closed",
               "closed permanently": "permanently closed", "closed temporarily": "temporarily closed"}
    return aliases.get(text, text)


def filter_reason(row, settings):
    """First reason for exclusion, or None. Numeric filters exclude unknown values."""
    for key, field, lower in (("min_rating", "review_rating", True), ("max_rating", "review_rating", False),
                              ("min_reviews", "review_count", True), ("max_reviews", "review_count", False),
                              ("min_score", "lead_score", True)):
        threshold = settings.get(key)
        if threshold is not None:
            value = number(row.get(field))
            if value is None or (value < threshold if lower else value > threshold):
                return key
    category = str(row.get("category") or "").casefold()
    if settings.get("category") and not any(c.casefold() in category for c in settings["category"]):
        return "category"
    if any(c.casefold() in category for c in settings.get("exclude_category") or []):
        return "exclude_category"
    for flag, field in (("has_website", "website"), ("has_email", "emails"), ("has_phone", "phone")):
        if settings.get(flag) and not present(row.get(field)):
            return flag
    if settings.get("no_website") and present(row.get("website")):
        return "no_website"
    if settings.get("has_socials") and not has_social(row):
        return "has_socials"
    if settings.get("business_status") and status_key(row.get("status")) not in {
            status_key(s) for s in settings["business_status"]}:
        return "business_status"
    return None


def scoring_rules(profile="balanced", overrides=None):
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("Unknown score profile: " + str(profile))
    rules = {"weights": dict(PROFILES[profile]), "rating_min": 4.0, "reviews_min": 30}
    if overrides is not None:
        if not isinstance(overrides, dict) or set(overrides) - {"weights", "rating_min", "reviews_min"}:
            raise ValueError("Scoring accepts weights, rating_min and reviews_min only")
        weights = overrides.get("weights", {})
        if not isinstance(weights, dict) or set(weights) - SIGNALS:
            raise ValueError("Unknown scoring signal; see docs/pro.md")
        for key, value in weights.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError("Score weights must be numbers between 0 and 100")
            rules["weights"][key] = value
        for key in ("rating_min", "reviews_min"):
            if key in overrides:
                value = overrides[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(key + " must be a nonnegative number")
                rules[key] = value
        if rules["rating_min"] > 5:
            raise ValueError("rating_min must be between 0 and 5")
    return rules


def score_lead(row, rules):
    rating, reviews = number(row.get("review_rating")), number(row.get("review_count"))
    signals = {"phone": present(row.get("phone")), "email": present(row.get("emails")),
               "website": present(row.get("website")), "missing_website": not present(row.get("website")),
               "socials": has_social(row), "rating": rating is not None and rating >= rules["rating_min"],
               "reviews": reviews is not None and reviews >= rules["reviews_min"],
               "website_unreachable": row.get("website_status") in {"unreachable", "http_error"},
               "no_https": row.get("website_https") is False,
               "no_contact_link": row.get("website_status") == "reachable" and not row.get("website_contact_link")}
    matched = [(key, weight) for key, weight in rules["weights"].items() if weight and signals[key]]
    row["lead_score"] = min(100, round(sum(weight for _, weight in matched), 2))
    row["score_reasons"] = "; ".join(f"+{weight:g} {LABELS[key]}" for key, weight in matched) or "No scoring signals matched"
    return row


def read_json(path):
    with open(path, encoding="utf-8-sig") as source:
        return json.load(source)


def string_list(value, label, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty) or any(
            not isinstance(s, str) or not s.strip() for s in value):
        raise ValueError(label + " must be a list of nonempty strings")
    return list(dict.fromkeys(s.strip() for s in value))


def load_campaign(path):
    cfg = read_json(path)
    allowed = {"name", "keywords", "cities", "languages", "keywords_by_language", "filters", "scoring", "options"}
    if not isinstance(cfg, dict) or set(cfg) - allowed:
        raise ValueError("Unknown campaign keys; see examples/campaign.example.json")
    if "name" in cfg and (not isinstance(cfg["name"], str) or not cfg["name"].strip()):
        raise ValueError("Campaign name must be a nonempty string")
    if "keywords" in cfg:
        cfg["keywords"] = string_list(cfg["keywords"], "keywords")
    if "languages" in cfg:
        cfg["languages"] = string_list(cfg["languages"], "languages")
    variants = cfg.get("keywords_by_language", {})
    if not isinstance(variants, dict) or any(not isinstance(k, str) or not k for k in variants):
        raise ValueError("keywords_by_language must map language codes to keyword lists")
    for lang, terms in variants.items():
        variants[lang] = string_list(terms, "keywords_by_language." + lang)
    cities = cfg.get("cities", [])
    if not isinstance(cities, list):
        raise ValueError("cities must be a list")
    for city in cities:
        if isinstance(city, str) and city.strip():
            continue
        if not isinstance(city, dict) or set(city) - {"name", "lat", "lon", "grid", "radius", "zoom", "names"}:
            raise ValueError("Each city needs a name and optional lat/lon/grid/radius/zoom/names")
        if not isinstance(city.get("name"), str) or not city["name"].strip():
            raise ValueError("City name must be a nonempty string")
        if ("lat" in city) != ("lon" in city):
            raise ValueError("City lat and lon must be provided together")
        if "lat" in city:
            if number(city["lat"]) is None or not -90 <= number(city["lat"]) <= 90 or number(city["lon"]) is None or not -180 <= number(city["lon"]) <= 180:
                raise ValueError("Invalid city coordinates")
        for key, low, high in (("grid", 1, 10), ("radius", 1, 1000000), ("zoom", 1, 21)):
            if key in city and (type(city[key]) is not int or not low <= city[key] <= high):
                raise ValueError(f"City {key} must be an integer between {low} and {high}")
        names = city.get("names", {})
        if not isinstance(names, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in names.items()):
            raise ValueError("City names must map language codes to nonempty names")
    for group, allowed_keys in (("filters", FILTER_KEYS), ("options", OPTION_KEYS)):
        if not isinstance(cfg.get(group, {}), dict) or set(cfg.get(group, {})) - allowed_keys:
            raise ValueError("Unknown " + group + " keys in campaign")
    scoring = cfg.get("scoring", {})
    if not isinstance(scoring, dict) or set(scoring) - {"profile", "weights", "rating_min", "reviews_min"}:
        raise ValueError("Unknown scoring settings in campaign")
    scoring_rules(scoring.get("profile", "balanced"), {k: v for k, v in scoring.items() if k != "profile"})
    return cfg


def coverage(rows):
    n = len(rows)
    counts = {"phone": sum(present(r.get("phone")) for r in rows),
              "email": sum(present(r.get("emails")) for r in rows),
              "website": sum(present(r.get("website")) for r in rows),
              "socials": sum(has_social(r) for r in rows)}
    return {key: {"count": count, "percent": round(count * 100 / n, 2) if n else 0}
            for key, count in counts.items()}


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def csv_value(value):
    """Keep CSV contact text from being interpreted as spreadsheet formulas."""
    text = str(value) if value is not None else ""
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else value


def write_results(path, rows, fields, fmt, report, rtl=False):
    ensure_parent(path)
    if fmt == "xlsx":
        write_xlsx(path, rows, fields, report, rtl)
    elif fmt == "json":
        with open(path, "w", encoding="utf-8") as target:
            json.dump(rows, target, indent=2, ensure_ascii=False)
    else:
        with open(path, "w", newline="", encoding="utf-8-sig") as target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            writer.writerows({k: csv_value(v) for k, v in row.items()} for row in rows)


# Native SpreadsheetML packaged with zipfile; runtime remains standard-library only.
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("", NS)
ET.register_namespace("r", REL)


def tag(name):
    return "{" + NS + "}" + name


def xml_text(value):
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value if value is not None else "")
    return "".join(c for c in text if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF)[:32767]


def col_name(n):
    result = ""
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def worksheet(headers, rows, rtl=False):
    if len(rows) > 1048575 or len(headers) > 16384:
        raise ValueError("Excel sheet limit exceeded; use CSV or JSON")
    root = ET.Element(tag("worksheet"))
    last = f"{col_name(len(headers))}{max(1, len(rows) + 1)}"
    ET.SubElement(root, tag("dimension"), ref="A1:" + last)
    views = ET.SubElement(root, tag("sheetViews"))
    view = ET.SubElement(views, tag("sheetView"), workbookViewId="0", rightToLeft="1" if rtl else "0")
    ET.SubElement(view, tag("pane"), ySplit="1", topLeftCell="A2", activePane="bottomLeft", state="frozen")
    ET.SubElement(view, tag("selection"), pane="bottomLeft", activeCell="A2", sqref="A2")
    ET.SubElement(root, tag("sheetFormatPr"), defaultRowHeight="32")
    cols = ET.SubElement(root, tag("cols"))
    for i, key in enumerate(headers, 1):
        width = 55 if key in {"score_reasons", "website_opportunities", "value", "error"} else 36 if key in {"title", "address", "keywords"} else 27
        if key in {"lead_score", "review_count", "review_rating", "count", "percent"}:
            width = 17
        ET.SubElement(cols, tag("col"), min=str(i), max=str(i), width=str(width), customWidth="1")
    data = ET.SubElement(root, tag("sheetData"))
    links = []
    numeric = {"lead_score", "review_count", "review_rating", "website_http_status", "count", "percent",
               "raw_rows", "unique_rows", "outside_bbox", "duplicates_removed", "exported_rows", "cell", "rows"}
    for ri, values in enumerate([headers] + rows, 1):
        row = ET.SubElement(data, tag("row"), r=str(ri), ht="32" if ri == 1 else "44", customHeight="1")
        for ci, value in enumerate(values, 1):
            address = f"{col_name(ci)}{ri}"
            text = xml_text(value)
            is_link = ri > 1 and text.startswith(("https://", "http://")) and not any(c.isspace() for c in text)
            style = "1" if ri == 1 else "3" if is_link else "2"
            cell = ET.SubElement(row, tag("c"), r=address, s=style)
            n = number(value)
            # Strings remain explicit strings, including formula-looking scraped text.
            if ri > 1 and (isinstance(value, (int, float)) and not isinstance(value, bool) or headers[ci - 1] in numeric) and n is not None:
                ET.SubElement(cell, tag("v")).text = str(n)
            else:
                cell.set("t", "inlineStr")
                inline = ET.SubElement(cell, tag("is"))
                ET.SubElement(inline, tag("t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}).text = text
            if is_link:
                links.append((address, text))
    ET.SubElement(root, tag("autoFilter"), ref="A1:" + last)
    if "lead_score" in headers and rows:
        column = col_name(headers.index("lead_score") + 1)
        cf = ET.SubElement(root, tag("conditionalFormatting"), sqref=f"{column}2:{column}{len(rows) + 1}")
        rule = ET.SubElement(cf, tag("cfRule"), type="colorScale", priority="1")
        scale = ET.SubElement(rule, tag("colorScale"))
        ET.SubElement(scale, tag("cfvo"), type="num", val="0")
        ET.SubElement(scale, tag("cfvo"), type="num", val="100")
        ET.SubElement(scale, tag("color"), rgb="FFF1F5F9")
        ET.SubElement(scale, tag("color"), rgb="FF6EE7B7")
    rels = ET.Element("Relationships", xmlns=PKG)
    if links:
        hyperlinks = ET.SubElement(root, tag("hyperlinks"))
        for index, (address, url) in enumerate(links, 1):
            rid = "rId" + str(index)
            ET.SubElement(hyperlinks, tag("hyperlink"), {"ref": address, "{" + REL + "}id": rid})
            ET.SubElement(rels, "Relationship", Id=rid, Type=REL + "/hyperlink", Target=url, TargetMode="External")
    ET.SubElement(root, tag("pageMargins"), left="0.3", right="0.3", top="0.5", bottom="0.5", header="0.2", footer="0.2")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), ET.tostring(rels, encoding="utf-8", xml_declaration=True)


STYLES = '''<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3"><font><sz val="11"/><name val="Calibri"/><color rgb="FF172033"/></font><font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font><font><u/><sz val="11"/><name val="Calibri"/><color rgb="FF0563C1"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF16324F"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''


def write_xlsx(path, rows, fields, report, rtl=False):
    summary = [["Campaign", report["name"]], ["Status", report["status"]],
               ["Started (UTC)", report["started_at"]], ["Elapsed seconds", report["elapsed_seconds"]]]
    summary.extend([[key, value] for key, value in report["totals"].items()])
    for group in ("collected_coverage", "exported_coverage"):
        for field, metric in report[group].items():
            summary.extend([[group + ": " + field + " count", metric["count"]],
                            [group + ": " + field + " percent", metric["percent"]]])
    summary.append(["Coverage denominator", "Collected: unique in-area leads before filters. Exported: leads after filters."])
    summary.append(["Scoring", "Rule-based priority (0-100), not a prediction of purchase intent. See Settings for rules."])
    summary.append(["Website checks", "A failed request is an observation, not proof that a business website is broken."])
    location_fields = ["city", "raw_rows", "unique_rows", "duplicates_removed", "outside_bbox", "exported_rows"]
    job_fields = ["city", "language", "cell", "job_id", "status", "rows", "error"]
    sheets = [("Summary", ["metric", "value"], summary),
              ("Leads", fields, [[r.get(f, "") for f in fields] for r in rows]),
              ("Locations", location_fields, [[r.get(f, "") for f in location_fields] for r in report["locations"]]),
              ("Jobs", job_fields, [[r.get(f, "") for f in job_fields] for r in report["jobs"]]),
              ("Settings", ["setting", "value"], [[k, v] for k, v in report["settings"].items()])]
    content = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    ET.SubElement(content, "Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(content, "Default", Extension="xml", ContentType="application/xml")
    for part, typ in (("/xl/workbook.xml", "sheet.main"), ("/xl/styles.xml", "styles")):
        ET.SubElement(content, "Override", PartName=part, ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml." + typ + "+xml")
    workbook = ET.Element(tag("workbook"))
    ET.SubElement(ET.SubElement(workbook, tag("bookViews")), tag("workbookView"), activeTab="0")
    entries = ET.SubElement(workbook, tag("sheets"))
    rels = ET.Element("Relationships", xmlns=PKG)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, (name, headers, values) in enumerate(sheets, 1):
            ET.SubElement(entries, tag("sheet"), {"name": name, "sheetId": str(index), "{" + REL + "}id": "rId" + str(index)})
            ET.SubElement(rels, "Relationship", Id="rId" + str(index), Type=REL + "/worksheet", Target=f"worksheets/sheet{index}.xml")
            ET.SubElement(content, "Override", PartName=f"/xl/worksheets/sheet{index}.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
            xml, sheet_rels = worksheet(headers, values, rtl)
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
            archive.writestr(f"xl/worksheets/_rels/sheet{index}.xml.rels", sheet_rels)
        ET.SubElement(rels, "Relationship", Id="styles", Type=REL + "/styles", Target="styles.xml")
        archive.writestr("[Content_Types].xml", ET.tostring(content, encoding="utf-8", xml_declaration=True))
        archive.writestr("_rels/.rels", f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", ET.tostring(workbook, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/_rels/workbook.xml.rels", ET.tostring(rels, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/styles.xml", STYLES)

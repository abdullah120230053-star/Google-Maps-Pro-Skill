# Google Maps Scraper PRO

The PRO Python CLI adds targeting, explainable scores, multi-city campaigns, Arabic/English searches,
published social links, website observations, native Excel workbooks and campaign reports. It uses
Python 3.9+ and the standard library only. Start the local engine with `docker compose up -d` first.
On Windows use `python` or `py`; the examples below use `python`.

## Quick examples

```powershell
python scripts/scrape.py "dentists in Cairo, Egypt" --city "Cairo, Egypt" --min-reviews 30 --has-phone --website-check --out output/cairo.xlsx
python scripts/scrape.py "dentists in {city}" --city "Cairo, Egypt" --city "Giza, Egypt" --score-profile website-services --out output/egypt.xlsx
python scripts/scrape.py --campaign examples/campaign.example.json --out output/campaign.xlsx
python scripts/scrape.py "عيادات أسنان في {city}" --city "القاهرة، مصر" --lang ar --min-rating 4 --out output/arabic.xlsx
```

CSV remains the default. `--out leads.xlsx` (or `--xlsx`) selects Excel; `.json` or `--json` selects JSON.
An explicit format must match the filename extension. Parent directories are created automatically.
The Bash wrapper accepts the original `keyword lat lon [depth]` arguments and forwards extra CLI options.

## Filters

All enabled filters must match. Category inclusions are ORed; exclusions always remove a match.
Filtering happens after enrichment, using complete rows even when `--fields` selects fewer columns.

- `--min-rating 4 --max-rating 5`: inclusive rating bounds, 0..5.
- `--min-reviews 30 --max-reviews 500`: inclusive nonnegative review counts.
- `--category dentist --category clinic`: case-insensitive category substrings.
- `--exclude-category hospital`: exclude matching categories; repeatable.
- `--has-website` / `--no-website`: website field present / absent. These do not test reachability.
- `--has-email`, `--has-phone`, `--has-socials`: require a nonempty contact field or discovered social URL.
- `--business-status operational`: exact listing status; repeatable, case-insensitive, underscores become spaces.
  `open` maps to `operational`; `permanently closed` and `temporarily closed` support common Arabic labels too.
  Status is the source listing status, not a live open-now check. Inspect raw `status` if the source uses another label.
- `--min-score 60`: require the calculated score, 0..100.

Unknown ratings, counts and statuses do not pass filters requiring those values. Arabic digits and decimal
separators are supported. Empty email/social cells mean unavailable, not a failed deliverability or identity check.

## Lead scoring

Every lead gets `lead_score` and `score_reasons`, and results sort by descending score with stable ties.
Scores are configurable rules capped at 100, not predictions of buying intent.

The default `balanced` profile awards phone 20, email 25, listed website 15, social link 10,
rating >=4 another 15 and reviews >=30 another 15.

`--score-profile website-services` prioritizes no website (35), observed request failure (25),
HTTP final pages (10), no detected homepage contact link (10), phone (20), email (10),
reviews >=30 (15) and rating >=4 (5). Website checks are enabled automatically for rules that need them,
unless explicitly disabled. A blocked, untested or non-HTML page does not earn a missing-contact-link score.
HTTP 401/403/429 is treated as blocked, not as an unreachable-site opportunity.

```powershell
python scripts/scrape.py "dentists in Cairo" --city Cairo --score-config examples/scoring.example.json --min-score 50 --out output/qualified.xlsx
```

Scoring JSON accepts `weights`, `rating_min` and `reviews_min`. Weights override the selected profile;
set a weight to 0 to disable a rule. Supported signals are `phone`, `email`, `website`, `missing_website`,
`socials`, `rating`, `reviews`, `website_unreachable`, `no_https`, `no_contact_link`.
Each weight must be 0..100. Reasons show each award before the total is capped.

## Multi-city and bilingual campaigns

Use repeated `--city` arguments or a JSON file like [campaign.example.json](../examples/campaign.example.json).
Multi-city keywords must contain `{city}` so a query for one city is never reused accidentally in another.
`{lang}` is also supported. For a single city, existing fully specified queries continue to work.

Campaign keys:

- `name`: campaign label, used in the engine and report.
- `keywords`: shared list of search terms/templates.
- `keywords_by_language`: optional language-specific term lists; overrides shared terms for that language.
- `cities`: names or objects with `name`, optional paired `lat`/`lon`, `grid` (1..10), `radius` (meters),
  `zoom`, and `names` such as `{"ar":"القاهرة، مصر","en":"Cairo, Egypt"}`.
- `languages`: `["en"]`, `["ar"]` or `["en","ar"]`.
- `filters`: CLI names with underscores, such as `min_reviews`, `has_phone`, `category` (list), `business_status` (list).
- `scoring`: optional `profile`, `weights`, `rating_min`, `reviews_min`.
- `options`: `depth`, `max_time`, `grid`, `email`, `deep_emails`, `socials`, `website_check`, `rtl`.

Explicit CLI settings override saved global settings. CLI cities replace the saved city list; CLI
languages/categories/statuses replace their saved lists. CLI keywords replace shared saved terms;
language-specific terms still take precedence. `--grid` overrides saved city grids too. Per-city
radius/zoom apply to non-grid searches; grid geometry determines these values for tiled searches.

Each city/language/grid combination is a separate job, run sequentially. Geocoding is once per city,
with a one-second pause between successful Nominatim lookups. Grid mode needs a city bounding box even
when explicit coordinates exist. A grid clips to that box with a 10% margin; ordinary searches use the
engine's location bias, not an administrative-boundary guarantee. Coverage is not guaranteed exhaustive.

Rows are deduplicated by `place_id`, then `cid`, then Maps link, then title+address. First listing values
win; matching rows merge their city/language attribution. `campaign_cities` and `search_languages` show
where a lead was found. Deduplication covers this run only; there is no persistent lead database.

`--lang` controls the engine listing language; it does not translate keywords automatically. Supply
Arabic variants yourself in `keywords_by_language`. Contact/about discovery recognizes Arabic labels,
and CSV/JSON files use explicit UTF-8. CSV includes a BOM for Excel. Arabic campaigns automatically
use right-to-left Excel sheets; `--rtl` enables this for other campaigns too. Column keys and CLI
messages remain English to keep integrations stable.

## Social profile links

Social discovery is **on by default**; `--no-socials` skips it. No extra prompt is required.
The script reads published links from business homepages, with one contact/about-page fallback when
the homepage contains no profiles. It also recognizes a social profile used as the listing website.

Columns: `instagram`, `facebook`, `linkedin`, `youtube`, `tiktok`, `x`, `whatsapp`.
Each has a corresponding `<platform>_source` URL. Only published links are returned; WhatsApp links
are not invented from phone numbers. Share/login links are skipped; post/video links are normalized
to profile links when their owner path is available. A discovered link is not verified ownership.
Social platforms themselves are not crawled to collect bios or private contact information.
Sites without published links will have empty cells. Discovery runs in code and does not use an LLM.

## Website opportunity checks

`--website-check` adds homepage observations:

- `website_status`: `missing`, `reachable`, `non_html`, `blocked`, `http_error`, `unreachable`, `invalid_url`, `social_profile`.
- `website_http_status`, `website_final_url`: response code and URL after redirects.
- `website_https`: true/false for successful responses, empty when unknown.
- `website_contact_link`: a detected same-site English/Arabic contact/about link.
- `website_opportunities`: observations to review manually.

This is a bounded homepage check, not a site crawl, security audit, performance test or permanent
broken-site verdict. Errors can reflect networking, bot protection or temporary downtime. Enrichment
shares a bounded in-process page cache across email, social and website checks.

## Exports and reporting

Default output includes the eight lead fields, city/language attribution, scores/reasons and social
links/sources. Website columns are included when checks are enabled. `--full` adds raw engine fields;
`--fields "title,phone,instagram,lead_score"` chooses exact columns without disabling enrichment/filtering.

Excel workbooks contain five sheets: **Summary**, **Leads**, **Locations**, **Jobs**, **Settings**.
They include frozen headers, filters, clickable HTTP(S) URLs, numeric score/rating/count cells, score
colors, wrapped text and Arabic-compatible text. Scraped text is stored as text, never as formulas.
CSV prefixes formula-like text (including leading `+` phone numbers) with an apostrophe for spreadsheet
safety. Use XLSX for typed text without that CSV prefix, or JSON for unchanged contact strings.

Every run writes `<output stem>.report.json`; `--report` selects another path. The report includes
elapsed time, job failures, unique and duplicate counts, out-of-area rows, filter exclusions, contact
coverage before/after filtering, and per-city counts. Coverage counts businesses with a field, not
individual contact addresses. City totals can overlap when a lead appears in several cities.
Reports retain complete metrics even if `--fields` hides contact fields in the exported leads.
If polling fails or expires while an engine job may still be active, the runner stops creating new
jobs, saves available results and reports how many jobs were not started. Check the engine job before retrying.

Exit codes: **0** complete (including legitimately empty results), **1** all jobs/locations failed,
**2** partial completion. Invalid arguments/configuration also exit 2 before starting jobs. Partial
and failed runs still save available results and a report. A startup connection failure exits 1.
Reports and exports may contain business/contact data; output folders and result files are git-ignored.

## Development checks

```powershell
python -m unittest discover -s scripts -p "test_*.py" -v
```

Tests use mocked/local engine responses and synthetic businesses; they do not scrape Google Maps.

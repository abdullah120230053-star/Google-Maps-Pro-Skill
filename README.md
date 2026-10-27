# Google Maps Scraper PRO

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

**Turn a business type and a city into a filtered, scored lead list with emails, social links and Excel exports.**

Google Maps Scraper PRO runs locally and supports single searches, multi-city campaigns, Arabic and
English queries, website opportunity checks, and campaign reports. The Python client uses only the
standard library: **no pip packages, Google Maps API key or scraping subscription are required**.
The scraping engine runs in Docker; an AI coding agent is optional.


## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Install and run](#install-and-run)
- [Usage examples](#usage-examples)
- [Saved campaigns](#saved-campaigns)
- [Filters](#filters)
- [Lead scoring](#lead-scoring)
- [Social profile links](#social-profile-links)
- [Website opportunity checks](#website-opportunity-checks)
- [Exports and reports](#exports-and-reports)
- [Configuration](#configuration)
- [Use with an AI agent](#use-with-an-ai-agent)
- [Troubleshooting](#troubleshooting)
- [Limits and responsible use](#limits-and-responsible-use)
- [Development and contributions](#development-and-contributions)
- [Credits and license](#credits-and-license)

## Features

- **Lead filtering:** rating/review ranges, categories, exclusions, listing status, contact availability and minimum score.
- **Explainable scoring:** configurable rules, two built-in profiles, reasons beside every score, and priority sorting.
- **Multi-city campaigns:** per-city coordinates or grids, sequential jobs, deduplication and city/language attribution.
- **Arabic and English:** language-specific keywords, localized city names, Arabic contact-page discovery and UTF-8 output.
- **Published contact enrichment:** website emails, a second contact/about-page email pass, and social URLs with discovery sources.
- **Website observations:** homepage response status, final URL, HTTPS and detected contact/about links.
- **Excel, CSV and JSON:** native `.xlsx` workbooks, Arabic right-to-left sheets, clickable links and spreadsheet-safe text.
- **Campaign reports:** unique/duplicate counts, exclusions, per-city results, contact coverage, elapsed time and partial failures.
- **Agent support:** instructions for Codex, Claude Code and other agents that can run local scripts.

## Requirements

| Requirement | Purpose |
|---|---|
| [Python 3.9 or newer](https://www.python.org/downloads/) | Runs the CLI, enrichment and exports |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine with Compose | Runs the scraper engine |
| [Git](https://git-scm.com/downloads) | Clones this repository; downloading a ZIP also works |
| Internet access | Reaches Google Maps, OpenStreetMap geocoding and business websites |

Windows users can run the Python CLI directly from PowerShell. macOS/Linux users usually use
`python3` instead of `python`. The Bash wrapper requires Bash, Git Bash or WSL.

The Docker image is pinned to `gosom/google-maps-scraper:v1.18.1`. First startup downloads the
image/browser components and can take several minutes. Apple Silicon may need amd64 emulation;
see [SETUP.md](SETUP.md).

## Install and run

### 1. Get the project

```bash
git clone https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill.git
cd Google-Maps-Pro-Skill
```

Alternatively, choose **Code → Download ZIP** on GitHub, extract it, and open a terminal in that folder.
Keep the entire repository together: the skill, scripts and Docker configuration work as a unit.

### 2. Check the prerequisites

```bash
python --version
docker --version
docker compose version
```

Use `py --version` on Windows or `python3 --version` on macOS/Linux if `python` is unavailable.
Make sure Docker Desktop/the Docker daemon is running before continuing.

### 3. Start the engine

```bash
docker compose up -d
docker compose ps
```

Wait until the engine responds:

- Web UI: [http://localhost:8080](http://localhost:8080)
- Job API: [http://localhost:8080/api/v1/jobs](http://localhost:8080/api/v1/jobs)
- API documentation: [http://localhost:8080/api/docs](http://localhost:8080/api/docs)

The job endpoint should return a JSON array, often `[]` on a fresh installation.
The engine is intentionally bound to `127.0.0.1` because it has no built-in authentication.

### 4. Run your first search

From the repository folder:

```bash
python scripts/scrape.py "dentists in Cairo, Egypt" --city "Cairo, Egypt" --min-reviews 30 --has-phone --website-check --out output/cairo.xlsx
```

This collects listings, enriches contacts/social links, checks homepages, applies filters, scores
the retained leads and saves:

- `output/cairo.xlsx`: formatted results and summary workbook.
- `output/cairo.report.json`: campaign metrics and failures.

Output folders are created automatically. Email extraction, the deep email pass, social discovery
and scoring are on by default. Discovery may find only a fraction of contacts; empty fields are normal.

## Usage examples

All commands below run from the repository root. Replace `python` with your platform's Python command if needed.

### One business type and city

```bash
python scripts/scrape.py "coffee shops in Austin TX" --city "Austin, TX" --out output/austin.csv
```

Already know the coordinates? Pass them directly; use `--` before the positional arguments so negative
longitudes are handled consistently:

```bash
python scripts/scrape.py --depth 5 --out output/miami.csv -- "gyms in Miami FL" 25.7617 -80.1918
```

### Qualified leads

```bash
python scripts/scrape.py "dental clinics in Cairo" --city "Cairo, Egypt" --min-rating 4 --min-reviews 30 --has-phone --out output/qualified.xlsx
```

Find listings without a website, ranked for a website-services offer:

```bash
python scripts/scrape.py "dentists in Cairo" --city "Cairo, Egypt" --no-website --has-phone --score-profile website-services --out output/website-opportunities.xlsx
```

`--no-website` means the listing's website field is empty. It does not mean a listed website failed a request.

### Multiple cities

```bash
python scripts/scrape.py "dentists in {city}" --city "Cairo, Egypt" --city "Giza, Egypt" --score-profile website-services --out output/egypt.xlsx
```

Multi-city keywords **must contain `{city}`** so each search uses the correct location.
The CLI runs jobs sequentially and deduplicates their results.

### Arabic searches

```bash
python scripts/scrape.py "عيادات أسنان في {city}" --city "القاهرة، مصر" --lang ar --min-rating 4 --out output/arabic.xlsx
```

Arabic campaigns automatically use right-to-left Excel sheets. `--rtl` enables that layout for any campaign.
The `--lang` option controls listing language; it does not translate search terms.

### A whole-city grid

```bash
python scripts/scrape.py "dentists in Cairo" --city "Cairo, Egypt" --grid 3 --out output/cairo-grid.xlsx
```

`--grid 3` creates 9 tiles per city and language. Grids help cover areas beyond one Maps search but
increase run time and rate-limit exposure. They do not guarantee every business is found.

### Several keywords

```bash
python scripts/scrape.py "dentists in Denver CO" --keyword "orthodontists in Denver CO" --city "Denver, CO" --out output/denver.xlsx
python scripts/scrape.py --keywords-file examples/queries.example.txt --city "Denver, CO" --out output/denver.csv
```

Keyword files use UTF-8, one query per line. Blank lines and lines beginning with `#` are ignored.

### A faster run without enrichment

```bash
python scripts/scrape.py "cafes in Austin TX" --city "Austin, TX" --no-email --no-socials --out output/quick.csv
```

To keep engine emails but skip the second contact-page pass, use `--no-deep-emails`.

## Saved campaigns

Edit [examples/campaign.example.json](examples/campaign.example.json), then run:

```bash
python scripts/scrape.py --campaign examples/campaign.example.json --out output/campaign.xlsx
```

A minimal bilingual campaign looks like this:

```json
{
  "name": "Egypt dental clinics",
  "keywords": ["dentists in {city}"],
  "keywords_by_language": {
    "ar": ["عيادات أسنان في {city}"]
  },
  "cities": [
    {
      "name": "Cairo, Egypt",
      "names": {"en": "Cairo, Egypt", "ar": "القاهرة، مصر"},
      "lat": "30.0444",
      "lon": "31.2357"
    },
    {
      "name": "Giza, Egypt",
      "names": {"en": "Giza, Egypt", "ar": "الجيزة، مصر"},
      "lat": "30.0131",
      "lon": "31.2089"
    }
  ],
  "languages": ["en", "ar"],
  "filters": {"min_reviews": 30, "has_phone": true},
  "scoring": {"profile": "website-services"},
  "options": {"depth": 5, "max_time": 600, "socials": true, "website_check": true}
}
```

City entries can also be plain names. Names are geocoded through OpenStreetMap Nominatim when coordinates
are absent. Grid mode always needs the city's bounding box, even when coordinates are provided.

Explicit CLI options override saved global settings. Repeated CLI cities, languages, categories and
statuses replace their saved lists. Language-specific keywords take precedence over shared keywords.
See [the PRO guide](docs/pro.md#multi-city-and-bilingual-campaigns) for the complete schema and precedence rules.

## Filters

All enabled filter groups must match. Repeated category inclusions use OR; exclusions remove matches.

| Option | Example / behavior |
|---|---|
| `--min-rating`, `--max-rating` | Inclusive bounds from 0 to 5 |
| `--min-reviews`, `--max-reviews` | Inclusive, nonnegative review-count bounds |
| `--category` | Case-insensitive category substring; repeat for alternatives |
| `--exclude-category` | Exclude category substrings; repeatable |
| `--has-website` / `--no-website` | Require a present / absent listing website |
| `--has-email` | Require an email after enrichment |
| `--has-phone` | Require a listed phone number |
| `--has-socials` | Require at least one discovered social URL |
| `--business-status` | Exact listing status; repeatable; `open` maps to `operational` |
| `--min-score` | Retain leads at or above a score from 0 to 100 |

Missing numeric/status values do not pass filters that require those values. Status is source listing
data, not a live open-now check. Category matching supports Unicode text, including Arabic.

## Lead scoring

Each lead has `lead_score` and `score_reasons`. Results sort by descending score; ties retain collection order.
Scores are **explainable prioritization rules, not predictions of buying intent**.

- **`balanced` (default):** phone 20, email 25, listed website 15, social URL 10, rating ≥4 earns 15,
  reviews ≥30 earns 15.
- **`website-services`:** prioritizes no listed website, observed request failures, HTTP pages, missing
  detected contact links and contactable businesses. Website checks turn on automatically when rules need them,
  unless explicitly disabled.

Customize weights and thresholds with [examples/scoring.example.json](examples/scoring.example.json):

```bash
python scripts/scrape.py "dentists in Cairo" --city "Cairo, Egypt" --score-config examples/scoring.example.json --min-score 50 --out output/scored.xlsx
```

Weights override the selected profile; use 0 to disable a rule. The total is capped at 100, and reasons
show the individual awards. Full rules: [PRO scoring reference](docs/pro.md#lead-scoring).

## Social profile links

Social discovery is **on by default**. Use `--no-socials` to skip it.

Supported fields: `instagram`, `facebook`, `linkedin`, `youtube`, `tiktok`, `x`, `whatsapp`.
Each has a corresponding `<platform>_source` URL.

The script reads links published on business homepages, with a bounded contact/about-page fallback,
and recognizes social profiles used as listing websites. It does not invent handles or WhatsApp
links from phone numbers. Discovery runs in code without an LLM.

A discovered link is not verified business ownership. Businesses without sites or published links
can have empty social fields. This is not a social-platform bio scraper.

## Website opportunity checks

Add `--website-check` to record:

- `website_status`: missing, reachable, non-HTML, blocked, HTTP error, unreachable, invalid URL or social-profile listing.
- `website_http_status` and `website_final_url`.
- `website_https`: true/false when observed, empty when unknown.
- `website_contact_link`: a detected same-site English/Arabic contact/about link.
- `website_opportunities`: observations to review manually.

These are bounded homepage checks. A failed request may reflect bot protection, temporary downtime
or your network; it is not proof that a site is permanently broken. No performance/security audit is performed.

## Exports and reports

### Lead columns

Default output includes:

- Core fields: `title`, `phone`, `emails`, `website`, `category`, `address`, `review_rating`, `review_count`.
- Attribution: `campaign_cities`, `search_languages`.
- Priority: `lead_score`, `score_reasons`.
- Social URLs and their discovery-source fields.
- Website observations when checks are enabled.

Choose exact output columns or include raw engine fields:

```bash
python scripts/scrape.py "dentists in Cairo" --city "Cairo, Egypt" --fields "title,phone,emails,instagram,lead_score" --out output/selected.csv
python scripts/scrape.py "dentists in Cairo" --city "Cairo, Egypt" --full --out output/full.json
```

Filtering and enrichment still use complete rows when `--fields` hides columns.

### File formats

The `--out` extension selects `.xlsx`, `.csv` or `.json`. You can also use `--xlsx`, `--json`
or `--format`; an explicit format must match the filename extension.

Excel workbooks contain:

| Sheet | Contents |
|---|---|
| Summary | Campaign status, totals, coverage and elapsed time |
| Leads | Filtered leads, scores, contacts and links |
| Locations | Per-city counts; a lead may belong to several cities |
| Jobs | Individual job outcomes and errors |
| Settings | Campaign parameters and scoring rules |

Workbooks have frozen headers, filters, clickable HTTP(S) links, numeric score/rating/count cells,
wrapped text and score coloring. CSV uses UTF-8 with BOM for Excel; JSON uses UTF-8.
Formula-like CSV text, including leading `+` phone numbers, is apostrophe-prefixed for spreadsheet safety.
XLSX stores contact strings as text; JSON preserves them without that CSV prefix.

### Campaign reports and exit codes

Every collection run saves `<output stem>.report.json`. Use `--report` to choose a different path.
Without `--out`, results use a timestamped `results-...` filename.

Reports include jobs planned/attempted/failed/not started, duplicate and out-of-area counts, collected
and exported rows, exclusion reasons, contact coverage and elapsed time. Coverage counts businesses
with a field, not the number of contact addresses.

| Exit code | Meaning |
|---|---|
| `0` | Complete, including genuinely empty results |
| `1` | All collection jobs/locations failed, or startup connection failed |
| `2` | Partial campaign completion; also used for invalid arguments/configuration |

Partial/failed campaigns preserve available results and a report. A startup connection failure or
invalid arguments occurs before collection. If polling loses track of a potentially active job,
the CLI stops starting new jobs; check the engine before retrying.

## Configuration

The defaults work without a `.env` file. To customize them:

**PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux**

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `SCRAPER_PORT` | `8080` | Host port used by Compose and the CLI |
| `SCRAPER_BASE_URL` | Unset | Optional full API URL; overrides the CLI port setting |
| `SCRAPER_API_KEY` | Empty | Sends `X-API-Key` only when using an authenticating proxy |

If port 8080 is occupied, set `SCRAPER_PORT=8081` in `.env`, then run `docker compose up -d` again.
Remove/update an old `SCRAPER_BASE_URL` override so it does not point at the wrong port.
Shell environment variables take precedence over the file. The Docker container's internal port stays 8080.

The local engine needs no API key. Setting `SCRAPER_API_KEY` does **not** add authentication to the
engine by itself. Keep the API private unless you separately configure an authenticating proxy.

## Use with an AI agent

Clone the **whole repository** and open its folder in your agent.

- **Codex:** [AGENTS.md](AGENTS.md) routes the agent to the local skill and scripts.
- **Claude Code:** [CLAUDE.md](CLAUDE.md), the local skill and four slash commands provide the workflow.
- **Other agents:** point them to [.claude/skills/google-maps-scraper/SKILL.md](.claude/skills/google-maps-scraper/SKILL.md)
  and give them terminal access in the repository folder.

Example request:

> Find dental clinics across Cairo and Giza with at least 30 reviews and a phone number.
> Include social links, prioritize website opportunities and export to Excel.

Claude Code commands: `/scrape`, `/scrape-batch`, `/scrape-setup`, `/scrape-jobs`.
The skill includes social links by default, monitors the CLI and reports incomplete runs.
Copying only the `SKILL.md` file is insufficient because the runtime scripts live elsewhere in the repository.
An agent subscription/API cost, if any, is separate from this local tool.

## Troubleshooting

| Problem | What to check |
|---|---|
| Python command not found | Try `py` on Windows or `python3` on macOS/Linux; confirm version ≥3.9 |
| Docker connection error | Start Docker Desktop/the daemon; run `docker compose ps` |
| Scraper not reachable | Run `docker compose up -d`; wait for the job API; check `.env` overrides |
| Port already allocated | Change `SCRAPER_PORT` in `.env` and restart with Compose |
| Empty output | Check query/location, filters and report; try a smaller validation search |
| Missing emails/socials | Not every business publishes contacts; inspect website availability and coverage |
| Partial results / exit 2 | Read the report's Jobs/locations/errors; do not treat output as full coverage |
| Polling stopped with an active job ID | Inspect the engine UI/job status before launching another campaign |
| Arabic looks wrong in a spreadsheet | Prefer XLSX or import CSV as UTF-8; use `--lang ar` for Arabic listings |
| A lot of failed jobs | Inspect engine logs, reduce volume and consider proxies; failure alone does not prove rate limiting |
| Need the complete CLI reference | Run `python scripts/scrape.py --help` and read [docs/pro.md](docs/pro.md) |

Inspect logs with `docker compose logs --tail 100`.
Stop the engine with `docker compose stop`; `docker compose down` removes the container but keeps named data volumes.
`docker compose down -v` also deletes stored job data, so use it only for an intentional reset.
More setup options and platform notes: [SETUP.md](SETUP.md).

## Limits and responsible use

- Search results depend on Google Maps and may be incomplete or change between runs. Grids improve coverage,
  not exhaustiveness. A regular search uses location bias rather than a guaranteed administrative boundary.
- Emails, social URLs and website checks depend on public source content and network access. Verify important leads.
- Deduplication covers one campaign run. Persistent lead history and crash-resume are not implemented.
- Jobs run sequentially. Large/repeated runs can trigger throttling. The engine supports proxy rotation
  through its API; this CLI does not expose a proxy flag.
- Nominatim is used for geocoding. Successful lookups are spaced by a one-second pause.
- Data is saved locally, but collection makes outbound requests to Maps-related services, OpenStreetMap
  and business websites. This is not an offline or anonymous workflow.
- Respect source terms and applicable privacy/contact-data rules. Do not use the project for individual
  surveillance, harassment or spam, and obtain appropriate authorization before outreach.
- Keep `.env`, leads and reports out of commits. Use the git-ignored `output/` directory for generated files.

## Development and contributions

Run the offline/local test suite:

```bash
python -m unittest discover -s scripts -p "test_*.py" -v
```

Tests use synthetic data and mocked/local HTTP services, not live Google Maps scraping.
The optional independent Excel-reader test runs when `openpyxl` is installed; it is not a runtime requirement.

Project layout:

```text
Google-Maps-Pro-Skill/
├── scripts/
│   ├── scrape.py          Engine API, geocoding and enrichment
│   ├── campaign.py        CLI and campaign orchestration
│   ├── pro.py             Filtering, scoring, reports and native Excel export
│   ├── scrape.sh          Bash compatibility wrapper
│   ├── test_scrape.py     Original and engine-flow tests
│   └── test_pro.py        PRO behavior and export tests
├── examples/             Keyword, campaign and scoring examples
├── docs/pro.md           Detailed PRO reference
├── .claude/              Agent skill, commands and local settings
├── AGENTS.md             Agent routing and development guidance
├── docker-compose.yml    Local engine deployment
└── .env.example          Optional configuration template
```

Keep the runtime dependency-free and preserve upstream notices.
Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Report bugs in [this repository's issues](https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill/issues).
Include your OS, Python version, command and a redacted error/report; do not upload private contacts or credentials.

## Credits and license

PRO repository: [abdullah120230053-star/Google-Maps-Pro-Skill](https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill).

Original kit: [Mahan / Mahanaicoach](https://github.com/Mahanaicoach/google-maps-scraper-kit).
Scraping engine: [Georgios Komninos / gosom](https://github.com/gosom/google-maps-scraper), used unmodified.

Released under the [MIT License](LICENSE). See [CREDITS.md](CREDITS.md) for upstream attribution
and the engine license notice.

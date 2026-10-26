---
name: google-maps-scraper
description: Build filtered, scored Google Maps business lead lists with multi-city campaigns, Arabic/English searches, published social profile links, website observations, Excel/CSV/JSON exports and campaign reports using the local gosom scraper. Use for local business research and contact enrichment, not direct social-platform scraping.
---

# Google Maps Scraper PRO

Run the kit's Python CLI from the repository root. It uses Python 3.9+ and the standard library.
The engine is the official `gosom/google-maps-scraper:v1.18.1` Docker image, bound to localhost.
Keep the MIT license and engine attribution intact.

## Run a lead search

1. Read `.env` if present to resolve `SCRAPER_PORT` / `SCRAPER_BASE_URL`. Check the engine with
   `GET /api/v1/jobs`; if it is down, start `docker compose up -d` from the kit root and check again.
   Do not print `SCRAPER_API_KEY` or expose the unauthenticated engine on a public interface.
2. Convert the user's business type, cities, languages and qualification requirements into CLI
   options. Use `--city` for one place or repeat it for several. Multi-city terms must contain
   `{city}`. For reusable or bilingual runs, use a campaign JSON file.
3. Run `python scripts/scrape.py ...` (or `python3`/`py`, depending on the host).
   Emails, a deep contact-page email pass, published social profile links and scoring are on by
   default. Honor explicit requests to skip enrichment. Social links are already authorized by
   the PRO workflow: do not ask an extra socials question.
4. Monitor the process through the current harness's background execution/session tools. The CLI
   polls the engine itself. Keep the user informed without loading individual website pages into
   the model's context.
5. Deliver the saved output plus a short report: collected/exported counts, contact coverage,
   failures and elapsed time. Show at most a few sample rows. Read the report even when the process
   exits nonzero: exit 2 can mean partial results, while 1 means failure. Never label partial
   coverage complete or guarantee that a city search found every business.

For filters, scoring rules, per-city options, report definitions and all PRO examples, read
[the PRO reference](../../../docs/pro.md). Use `python scripts/scrape.py --help` for exact flags.
The repository also contains `examples/campaign.example.json` and `examples/scoring.example.json`.

## Common requests

```bash
# Qualified leads, social profiles and homepage observations, exported to Excel
python scripts/scrape.py "dentists in Cairo, Egypt" --city "Cairo, Egypt" --min-reviews 30 --has-phone --website-check --out output/cairo.xlsx

# Several cities, ranked for a website-services offer
python scripts/scrape.py "dentists in {city}" --city "Cairo, Egypt" --city "Giza, Egypt" --score-profile website-services --out output/egypt.xlsx

# Arabic/English templates and localized city names
python scripts/scrape.py --campaign examples/campaign.example.json --out output/campaign.xlsx
```

- `--grid 3`: 3 x 3 sequential map tiles per city/language with deduplication and bounding-box clipping.
- `--lang ar` / `--lang en --lang ar`: listing languages. Supply translated search terms in
  `keywords_by_language`; language flags do not translate terms automatically.
- Default output: eight lead fields, city/language attribution, score/reasons and social URLs/sources.
  Website observations appear when enabled. `--full` includes raw fields; `--fields` chooses exact columns.
- Social fields: Instagram, Facebook, LinkedIn, YouTube, TikTok, X and published WhatsApp links.
  Links are discovered on business websites; ownership is not verified. Do not invent handles or
  WhatsApp URLs from phone numbers. Do not crawl social platforms for private data.
- Scores are explained, configurable priority rules (0..100), not buying-intent predictions.
- Website failures can reflect temporary networking or bot protection. Present the observed status,
  not a definitive verdict that a business website is broken.
- CSV uses UTF-8 with BOM; JSON uses UTF-8; Arabic Excel campaigns use right-to-left sheets.
  CSV formula-like text is apostrophe-prefixed; JSON preserves the original strings.

## Engine API invariants

Prefer the CLI. For custom API requests, these fields are required by `POST /api/v1/jobs`:
`keywords` (array with locations in the terms), `lat` and `lon` (strings), `max_time` (seconds).
Recommended defaults: depth 5, zoom 15, radius 10000, fast_mode false, email true.
Create returns lowercase `id`. `GET /api/v1/jobs/{id}` returns capitalized `Status`, with
`working`, `ok` or `failed`. Download CSV at `GET /api/v1/jobs/{id}/download`.
List at `GET /api/v1/jobs`; delete only user-selected jobs with `DELETE /api/v1/jobs/{id}`.
Proxy rotation is supported by the engine's `proxies` array; the kit CLI does not expose proxy flags.

## Operational boundaries

- Run engine jobs sequentially. For grids, many cities/keywords, repeated jobs or high depth, give
  one short rate-limit/time warning, suggest proxies and proceed within the user's request.
  If failures suggest blocking, explain the evidence and reduce volume or wait; do not promise a
  particular recovery time.
- Scraped contacts can be personal data. Keep full results on disk, preserve opt-out/suppression
  requirements for any later outreach, and do not initiate outreach without explicit authorization.
- Do not assist surveillance of individuals, harassment or spam. Keep legal and source terms
  considerations specific to the intended use rather than making blanket legal claims.
- Exports and reports contain data: keep them out of commits. Do not delete old engine jobs or
  volumes merely to clean up a scrape.

# Google Maps Scraper PRO in Python

The Python 3.9+ CLI uses only the standard library. It runs single searches, keyword batches,
multi-city bilingual campaigns, filters, lead scoring, contact/social enrichment, website checks,
CSV/JSON/Excel exports and campaign reports.

Start the Docker engine, then run:

```powershell
docker compose up -d
python scripts/scrape.py "dentists in {city}" --city "Cairo, Egypt" --city "Giza, Egypt" --min-reviews 30 --has-phone --website-check --out output/leads.xlsx
python scripts/scrape.py --campaign examples/campaign.example.json --out output/campaign.xlsx
python scripts/scrape.py --help
```

On Windows use `python` or `py`; on macOS/Linux `python3` is common.
Read **[the PRO guide](pro.md)** for all filters, profiles, campaign schemas and report definitions.

Emails and social links are on by default; `--no-email` and `--no-socials` skip them.
`--grid 3` splits each city into nine sequential jobs per language.
`--fields` chooses exact output columns while qualification still uses complete enriched rows.
Every run saves a JSON report next to its output. Partial completion exits 2 and preserves results.

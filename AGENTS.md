# Google Maps Scraper PRO

For business-lead requests, load `.claude/skills/google-maps-scraper/SKILL.md` and run the repository's
Python CLI. `docs/pro.md` documents filtering, scoring, campaigns, exports and report semantics.
Keep the engine bound to localhost. Social profile links are included by default; honor explicit opt-outs.
Deliver files and concise campaign metrics, and disclose partial results from the JSON report.

For development, preserve the dependency-free Python 3.9+ runtime and the engine's MIT attribution.
Keep HTTP/enrichment in `scripts/scrape.py`, orchestration in `scripts/campaign.py`, and targeting/export
helpers in `scripts/pro.py`. Run `python -m unittest discover -s scripts -p "test_*.py" -v` after code changes.
Tests should use synthetic/local data; do not launch live scraping jobs merely to validate a code edit.
Never commit generated leads or reports. Use `output/` for local results.

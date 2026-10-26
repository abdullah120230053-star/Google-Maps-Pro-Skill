# Contributing

This page tells you how to get a bug fixed or a change merged into the Google Maps Scraper Kit.

- **Report bugs** with the bug report issue template. Include the exact command and the full error.
- **Keep pull requests small**, one change each. Test with a `depth 1` scrape and run
  `python -m unittest discover -s scripts -p "test_*.py" -v` before you open the PR.
- **Keep the scripts portable.** `scripts/scrape.py` uses the Python standard library only, so do not
  add pip dependencies. `scripts/scrape.sh` must run on macOS's default bash 3.2. PRO CLI changes
  belong in `scripts/campaign.py`, targeting/export helpers in `scripts/pro.py`, and HTTP/enrichment
  changes in `scripts/scrape.py`. Update `docs/pro.md`, examples and skill guidance with CLI changes.
- **Send engine changes upstream.** Changes to the engine itself belong in
  [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper).
- **Never commit scrape output.** CSV and result files are git-ignored because they hold personal data.

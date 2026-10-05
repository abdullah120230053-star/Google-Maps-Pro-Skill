# Contributing

Thanks for helping improve the Google Maps Scraper Kit.

- **Bugs:** open an issue with the bug report template. Include the exact command and the full error.
- **Pull requests:** keep them small and focused on one change. Test with a `depth 1` scrape before you
  open the PR.
- **Scripts:** `scripts/scrape.py` uses the Python standard library only. Do not add pip dependencies.
  `scripts/scrape.sh` must run on macOS's default bash 3.2.
- **Scraping engine:** changes to the engine itself belong upstream in
  [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper).
- **Data:** never commit scrape output. CSV and result files are git-ignored because they hold
  personal data.

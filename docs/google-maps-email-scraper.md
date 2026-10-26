# Google Maps email scraper: how the kit finds business emails

The Google Maps Scraper Kit is a free Google Maps email scraper that runs on your own machine with no API key.
Name a business type and a city, and you get a CSV of local businesses with their published contact emails next to phone, website and address.

## How emails are found

Emails are on by default. Google Maps listings carry no email field, so the kit collects them from each business website in two steps.

1. The engine visits the website on every listing and pulls any email it can read there.
2. The deep email pass then takes each row that has a website but still no email. It fetches the homepage, then up to 3 contact and about pages on the same site.

The deep email pass reads `mailto:` links and plain text on those pages. It drops junk such as image file names, placeholder addresses and website-builder domains. It sorts addresses on the business's own domain first and keeps at most 3 per row. It runs in plain Python code, so it costs zero AI tokens.

When the pass ends, the script prints one found-rate line. It shows how many emails came from the engine, how many the contact pages added, and the total share of rows with an email.

## Run it

Start the engine once, then run a search with `--city` so you can skip coordinates:

```bash
docker compose up -d
python3 scripts/scrape.py "dentists in Denver CO" --city "Denver, CO" --depth 5
```

Skip the deep email pass for a quicker run, or skip emails entirely for the fastest run:

```bash
python3 scripts/scrape.py "dentists in Denver CO" --city "Denver, CO" --no-deep-emails
python3 scripts/scrape.py "dentists in Denver CO" --city "Denver, CO" --no-email
```

The CSV uses a timestamped `results-...csv` filename unless you pass `--out`; every run also saves a campaign report.

## Example output

Illustrative rows only:

| title | phone | emails | website | category |
|---|---|---|---|---|
| Example Dental Studio | +1 303-555-0101 | hello@example.com | example.com | Dentist |
| Sample Family Dentistry | +1 303-555-0102 | front@example.org, info@example.org | example.org | Dentist |
| Demo Smile Center | +1 303-555-0103 |  | example.net | Dentist |

The empty `emails` cell on the last row is normal. That site published no email the kit could read.

## What to expect

- Expect emails on a fraction of rows, not all of them. A business with no website, or a site with no visible email, returns an empty cell.
- Social profile links and their source URLs are included by default for Instagram, Facebook, LinkedIn, YouTube, TikTok, X and published WhatsApp links. Use `--no-socials` to skip discovery; Instagram bios are not scraped.
- Email extraction visits every website, so a run with emails is slower than one with `--no-email`.
- Google Maps returns about 120 listings per search. Add `--grid 3` to split the city into 9 map tiles and get past that cap, with duplicates removed.
- Heavy use without proxies can get your IP temporarily rate-limited by Google for minutes to hours. Run one job at a time and add proxies for large or repeated runs.
- Scraping Google Maps is against Google's Terms of Service and emails are personal data, so read [Responsible use](../README.md#limits-and-responsible-use) before you send anything.

## Related

- [Scrape Google Maps leads with Claude Code](scrape-google-maps-leads-with-claude-code.md)
- [Google Maps scraper in Python](google-maps-scraper-python.md)
- [Kit README](../README.md)

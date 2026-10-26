---
description: Run a multi-keyword or multi-city PRO campaign with scoring, social links and reports.
argument-hint: <keywords-file or campaign.json> [requirements]
---
Request: **$ARGUMENTS**

Load the `google-maps-scraper` skill and read `docs/pro.md`.
For a saved JSON campaign use `python scripts/scrape.py --campaign <file> --out output/leads.xlsx`.
For a plain UTF-8 keyword list use `--keywords-file <file> --city "<city>"`.
Several cities require `{city}` templates; use campaign `keywords_by_language` for Arabic/English variants.

Check/start the local engine, apply the user's filters and scoring requirements, and run sequential
jobs. Emails and published social links are included by default; respect requested opt-outs without
asking another socials question. Give one short rate-limit warning for large runs, then proceed.
Monitor with the current harness's background/session tools.

Deliver the output and JSON campaign report, explaining contact coverage, deduplication and failures.
Partial runs exit 2 but save available results; never present them as full coverage.

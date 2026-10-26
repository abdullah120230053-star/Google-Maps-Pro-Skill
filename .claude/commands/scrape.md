---
description: Run a filtered, scored Google Maps PRO lead search with social links and CSV/Excel output.
argument-hint: <business type> in <city> [requirements]
---
Request: **$ARGUMENTS**

Load the `google-maps-scraper` skill and use `scripts/scrape.py`.
Resolve the business type, city, language and qualification requirements. Read `docs/pro.md` when
filters, scoring, website checks or exports need configuration. Emails and social profile links are
on by default; do not ask an extra socials question. Honor explicit opt-outs.

Check/start the local engine. Run the CLI with the requested filters, score profile and output type.
For multiple cities use a `{city}` keyword template; for full-city coverage add `--grid 3`.
Use the current harness's background/session tools for long runs; the CLI handles polling.
For large jobs, give one short time/rate-limit warning and proceed.

Deliver the saved file and its campaign report, with exported/collected counts, contact coverage,
elapsed time and failed jobs. Exit 2 can indicate partial results: say so explicitly. Show only a few
sample leads. Scores are rule-based priorities, social links are discovered rather than ownership-
verified, and website checks are observations requiring review.

# CLAUDE.md: Google Maps Scraper PRO

You are working inside the **Google Maps Scraper Kit**. The kit runs a local Google Maps scraper for
lead generation, and you drive it for the user.

## What the kit is
A local Docker deployment of the open-source engine `gosom/google-maps-scraper`, exposed as a REST API
at **`http://localhost:8080`**, plus a skill that teaches you to use it. It scrapes **Google Maps
business listings only**, not social media.

## When the user asks for businesses, a list of places or lead data
**Load and follow the `google-maps-scraper` skill** (`.claude/skills/google-maps-scraper/SKILL.md`).
It has the exact API flow, the required fields, and the best-practice and safety rules. Do not write
the API calls from memory. Use the skill.

## PRO workflow
Use `python scripts/scrape.py` for single, batch, multi-city and bilingual campaigns. The CLI adds
filters, explainable scoring, social profile links/sources, optional website checks, native Excel
exports and JSON campaign reports. Read `docs/pro.md` and `--help` for the supported options.
Emails and social discovery are on by default; do not ask an extra social-profiles question. Honor
`--no-email` and `--no-socials` when requested. Multi-city keywords require `{city}` templates.
Prefer `.xlsx` output when the user wants Excel; use the full rows for enrichment/filtering and
project output columns only afterward. Check the JSON report: exit 2 can mean partial completion.
Never describe discovered profile links as verified ownership or website request failures as
proof of a permanently broken website. Python outputs and reports explicitly use UTF-8 for Arabic.

## Slash commands
The kit ships four commands in `.claude/commands/` that map to the skill: `/scrape` (single query),
`/scrape-batch` (many queries, one job), `/scrape-setup` (start the engine), `/scrape-jobs` (list or delete).
Local commands are pre-approved in `.claude/settings.json`, so you can run them without prompting the user.

## Rate limits: warn, don't block
If a request is large (high `depth`, many keywords, repeated runs, a grid, or `email:true`), **proceed**,
but first print ONE short warning that heavy use can get the user's IP temporarily rate-limited by
Google, and suggest proxies. Do NOT gate or demand confirmation for a normal big scrape. Refuse only
clearly abusive use (surveilling individuals, spam). The skill has the full guidance.

## Hard facts you must not get wrong
- API base: `http://localhost:8080`, with **no auth** because it is bound to localhost. Never expose it publicly.
- Create a job with `POST /api/v1/jobs`. These body fields are **required**, or it returns 422:
  `max_time` (in **seconds**, e.g. `300`), `lat` and `lon` (as **strings**), and `keywords` (array).
- The create response is `{"id":"<uuid>"}` (lowercase `id`). Check status with `GET /api/v1/jobs/{id}`; its field is `"Status"`, and it becomes `"ok"` when done.
- **Poll in the background.** The Bash tool blocks foreground `sleep`. Run the poll loop as a
  background/session tools provided by the current harness. The Python CLI polls jobs itself.
- Before a big job (high depth, many keywords), tell the user the cost once: time and IP rate-limit risk. Then proceed.
- Scraped emails and phones are **personal data**. Do not dump large CSVs into chat: summarize and save to disk.

## Setup
If the container is not running: `docker compose up -d`, then verify with `curl http://localhost:8080/api/v1/jobs`.
`SETUP.md` has the full setup.

## Attribution
The engine is `gosom/google-maps-scraper` (MIT, © Georgios Komninos), run as its official Docker image. Keep `CREDITS.md` and `LICENSE` intact.

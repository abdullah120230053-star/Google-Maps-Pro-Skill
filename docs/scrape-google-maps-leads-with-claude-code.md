# Run Google Maps Scraper PRO with a coding agent

Clone the whole repository and start the engine:

```bash
git clone https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill.git
cd Google-Maps-Pro-Skill
docker compose up -d
```

Python 3.9+ and Docker are required. The Python CLI has no pip dependencies.

## Open the local project

For Claude Code, start `claude` in the repository folder. It can read `CLAUDE.md`, the local
skill and four slash commands. For Codex, open the same folder; `AGENTS.md` routes to the skill.
Other terminal-capable agents can read `.claude/skills/google-maps-scraper/SKILL.md` directly.

Do not copy only the skill file: the CLI and configuration remain in the repository.
There is no required MCP server or Google Maps API key.

## Ask for leads

> Find dental clinics across Cairo and Giza with at least 30 reviews and a phone number.
> Include social links, prioritize website opportunities and export to Excel.

The agent should run `scripts/scrape.py`, monitor it using its execution/session tools, and deliver
the saved output and a short campaign summary. Emails, social discovery and scoring are on by default.
For multiple cities it uses `{city}` keyword templates; bilingual campaigns can use translated
keywords and localized city names from JSON.

Example CLI command:

```bash
python scripts/scrape.py --campaign examples/campaign.example.json --out output/campaign.xlsx
```

## Commands in Claude Code

- `/scrape`: one search with the requested qualification rules.
- `/scrape-batch`: a keyword file or saved multi-city campaign.
- `/scrape-setup`: start/check the local engine.
- `/scrape-jobs`: inspect, download or delete selected engine jobs.

The engine provides a local HTTP API at `http://localhost:8080`, or your configured port.

## What to expect

Excel output contains Summary, Leads, Locations, Jobs and Settings sheets.
The JSON report records coverage, exclusions, failures and elapsed time.
Partial campaigns exit 2 and save available results; the agent should state the gaps.
Social links are discovered, not ownership-verified; website failures are observations to review.

Read [the PRO guide](pro.md), [setup instructions](../SETUP.md), and
[limits and responsible use](../README.md#limits-and-responsible-use).

# Google Maps Scraper Kit

<p align="center">
  <img src="assets/banner.svg" alt="Google Maps Scraper Kit — local Google Maps lead extraction, operated by Claude" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0b1220?style=flat-square"></a>
  <img alt="Runs locally" src="https://img.shields.io/badge/runs-100%25%20local-059669?style=flat-square">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-skill%20%2B%20commands-7c3aed?style=flat-square">
  <img alt="No API keys" src="https://img.shields.io/badge/API%20keys-none-334155?style=flat-square">
</p>

**Local Google Maps lead extraction, operated by Claude.**
Name a business type and a city. Get back a clean, outreach-ready CSV: name, phone, email, website,
category, address, rating, and review count. Optional Instagram, Facebook, and LinkedIn enrichment.

Everything runs on your machine. No SaaS, no credits, no API keys.

---

## Why it exists

Ask a chat AI to "scrape Google Maps" and it hits a consent wall and JavaScript-rendered pages. Result:
close to zero structured rows. This kit runs a real headless scraping engine locally and gives Claude
a precise operating manual for it. Result: dozens to hundreds of verified listings per query.

## Capabilities

| | |
|---|---|
| **Lead-ready output** | The engine captures ~34 raw fields. The kit keeps the 8 you contact and qualify with, and writes a CSV. `--full` keeps everything. |
| **Email extraction** | On by default. Pulls contact emails from each business website. |
| **Social enrichment** | `--socials` finds Instagram, Facebook, and LinkedIn profiles. Runs in code (HTTP + regex), zero AI tokens. |
| **Auto-geocoding** | Type a city name. Coordinates are resolved for you. |
| **Batch jobs** | Many keywords, one job, one CSV. |
| **Claude-native** | A skill plus four slash commands. Claude handles create, poll, download, clean, and present. |
| **Safe defaults** | API bound to `127.0.0.1`, secrets git-ignored, rate-limit and data-law guardrails built into the skill. |

---

## Quick start

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop). Python 3 is optional (standard library only).

```bash
git clone https://github.com/Mahanaicoach/google-maps-scraper-kit.git
cd google-maps-scraper-kit
docker compose up -d
```

```bash
./scripts/scrape.sh "coffee shops in Austin TX" 30.2672 -97.7431 5
```

Or open the folder in Claude Code and say:

> Scrape gyms in Miami and give me phones and websites.

### Example output

`coffee_shops_austin.csv` (illustrative rows):

| title | phone | emails | website | category | address | review_rating | review_count |
|---|---|---|---|---|---|---|---|
| Example Roasters | +1 512-555-0101 | hello@example.com | example.com | Coffee shop | 100 Congress Ave, Austin, TX | 4.7 | 812 |
| Sample Espresso Bar | +1 512-555-0102 | info@example.org | example.org | Cafe | 200 S Lamar Blvd, Austin, TX | 4.5 | 356 |

Add `--socials` for `instagram`, `facebook` and `linkedin` columns, or `--full` for all ~34 raw fields.

Detailed setup: [SETUP.md](SETUP.md). Skill reference: [SKILL.md](.claude/skills/google-maps-scraper/SKILL.md).

---

## Using it in Claude Code

| Command | Action |
|---|---|
| `/scrape <business> in <city, ST> [depth]` | Run one scrape, return a clean table and CSV |
| `/scrape-batch <keywords-file> [--city "City, ST"]` | Run many queries as one job |
| `/scrape-setup` | Start the engine and run a health check |
| `/scrape-jobs [list \| delete <id>]` | List or delete jobs |

Plain language works too. The skill triggers on requests like *"build me a lead list of dentists in
Denver, CO"* or *"pull Google Maps listings for plumbers in Phoenix"*. It does not scrape social
platforms directly.

### Without Claude

`scripts/scrape.py` is a standalone, dependency-free Python CLI: single queries, batches, geocoding,
socials, CSV output. `scripts/scrape.sh` covers the single-query case in bash.

---

## Responsible use

This drives a real scraper against Google Maps. Light use is fine. Heavy use without proxies can get
your IP **temporarily rate-limited** (minutes to hours). Your Google account is not affected.

- Run one job at a time. Start at `depth 5` and raise only when needed.
- Watch for block signals: `failed` jobs, empty results, or far fewer rows than an identical earlier run.
- Add proxies for large or repeated runs. The engine rotates them automatically:
  ```json
  "proxies": ["socks5://user:pass@host:port", "http://host2:port2"]
  ```
  Supported: `socks5`, `socks5h`, `http`, `https`.
- Scraping Maps is against Google's Terms of Service. Treat output as leads to verify, not a dataset to
  resell. Phones and emails are personal data: follow GDPR, CCPA, and CAN-SPAM.

For large requests, Claude flags the risk and suggests proxies, then proceeds. It refuses only clearly
abusive use.

---

## Project layout

```
google-maps-scraper-kit/
├── docker-compose.yml      local engine on 127.0.0.1:8080
├── .env.example            config template
├── scripts/
│   ├── scrape.py           Python CLI: single, batch, geocoding, socials, CSV
│   └── scrape.sh           bash CLI: single query
├── examples/               sample job body and batch keyword list
├── .claude/
│   ├── settings.json       pre-approved local commands for hands-free runs
│   ├── commands/           /scrape, /scrape-batch, /scrape-setup, /scrape-jobs
│   └── skills/google-maps-scraper/SKILL.md
├── CLAUDE.md               project instructions for Claude Code
├── CREDITS.md              scraping engine attribution and license
└── SETUP.md                full setup guide
```

## Support

Found a bug? [Open an issue](https://github.com/Mahanaicoach/google-maps-scraper-kit/issues/new/choose) with
the command you ran and the error. Issues are for problems with the kit. Run your own scrapes with the
quick start above; requests like "find me hotels in Hamburg" are closed without action.
Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

Built by [Mahan](https://github.com/Mahanaicoach). MIT licensed. Third-party components: [CREDITS.md](CREDITS.md).

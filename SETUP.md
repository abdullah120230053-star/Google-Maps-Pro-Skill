# Setup guide: Google Maps Scraper PRO

The public [README](README.md#install-and-run) includes installation, examples, filters, scoring
and export instructions. This page covers environment setup and operational details.

## Prerequisites

- Python **3.9+**: [download Python](https://www.python.org/downloads/).
- Docker Desktop, or Docker Engine with the Compose plugin: [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- Git for cloning, or download/extract the repository ZIP.
- Internet access and enough disk space for the engine/browser image.

The CLI has no pip dependencies, including for Excel exports. An AI agent is optional.

## Get this repository

```bash
git clone https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill.git
cd Google-Maps-Pro-Skill
```

On Windows use PowerShell and `python` or `py`. On macOS/Linux use `python3` if needed.
Keep the repository intact; copying the skill file alone does not include its helper scripts.

## Optional local configuration

Defaults work without a configuration file. To customize the port:

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Edit `SCRAPER_PORT=8081` if 8080 is in use. Both Compose and the Python CLI read this file.
Shell environment variables take precedence. A nonempty `SCRAPER_BASE_URL` overrides the CLI port;
remove or update it if you change the port.

Leave `SCRAPER_API_KEY` empty for the default local engine. That variable only sends an HTTP
header to an optional authenticating proxy; it does not secure the engine itself.

## Start and verify

Start Docker Desktop/the daemon, then:

```bash
docker compose up -d
docker compose ps
docker compose logs --tail 100
```

The first start pulls the pinned `gosom/google-maps-scraper:v1.18.1` image and may take several minutes.
Check [the local job API](http://localhost:8080/api/v1/jobs): it should respond with a JSON array.

PowerShell health check:

```powershell
Invoke-RestMethod http://localhost:8080/api/v1/jobs
```

macOS/Linux health check:

```bash
curl -f http://localhost:8080/api/v1/jobs
```

Use your configured port if different. The web UI is at the API host's root; API docs are at `/api/docs`.
The Compose port mapping binds only to `127.0.0.1`. Keep this boundary: the engine has no built-in authentication.
Compose routes requests through a small Nginx proxy that serves the responsive PRO workspace,
project support links, and local API docs at `/api/docs`.
The OpenAPI JSON is available at `/api/openapi.json`. The engine stays internal to the Compose network.
The direct `docker run` fallback below runs the original interface without these customizations.

The web form creates engine jobs. It provides searchable history, status filters, details and raw
CSV downloads; active jobs cannot be deleted from the workspace. Use the Python CLI for PRO campaign
filtering, scoring, social enrichment and Excel output. Existing engine jobs remain available in both interfaces.

### Apple Silicon

The pinned image may need amd64 emulation. If necessary, uncomment `platform: linux/amd64` in
`docker-compose.yml`, then start it again. Emulation may be slower. For native-engine alternatives,
consult the [upstream engine instructions](https://github.com/gosom/google-maps-scraper).

### Docker is available but Compose is missing

Install the Compose plugin, or run the equivalent container directly (macOS/Linux/Git Bash syntax):

```bash
docker run -d --name gmaps-scraper --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -v gmaps_data:/gmapsdata -v gmaps_cache:/opt \
  gosom/google-maps-scraper:v1.18.1 -web -data-folder /gmapsdata
```

Use either Compose or the direct container, not both at the same time. If using direct Docker,
manage it with `docker stop gmaps-scraper` and `docker start gmaps-scraper`.

## Run a campaign

```bash
python scripts/scrape.py --campaign examples/campaign.example.json --out output/campaign.xlsx
```

Or start smaller:

```bash
python scripts/scrape.py "dentists in Cairo, Egypt" --city "Cairo, Egypt" --depth 1 --no-email --no-socials --out output/check.csv
```

Social links, email enrichment and scoring are normally on by default. The second command intentionally
skips enrichment for a quick validation. Choose your own query and inspect results before larger runs.

Read [docs/pro.md](docs/pro.md) for campaign schemas, all filters, scoring rules and reporting semantics.

## Use with an agent

Open this repository folder in Codex, Claude Code or another terminal-capable agent.
The project contains `AGENTS.md`, `CLAUDE.md`, the skill at
`.claude/skills/google-maps-scraper/SKILL.md`, and four Claude Code slash commands.

The agent should use the scripts in this checkout. Installing a differently named upstream skill
does not install this repository's PRO implementation.

## Troubleshooting

- **Python not found:** try `py` (Windows) or `python3` (macOS/Linux); confirm version 3.9+.
- **Docker daemon unavailable:** start it and run `docker compose ps`.
- **Port occupied:** change `SCRAPER_PORT` in `.env`; check for a stale `SCRAPER_BASE_URL` override.
- **Connection refused:** wait for engine startup and inspect `docker compose logs --tail 100`.
- **Image/browser startup fails:** inspect engine logs and report the image tag, platform and redacted error.
- **Empty output:** check the query, coordinates and filters; review the campaign report's counts.
- **Missing contact fields:** only published contact details can be discovered.
- **Exit 2 after jobs ran:** results may be partial; inspect the report before retrying.
- **Polling lost track of a job:** check that job in the engine UI before launching another campaign.
- **Slow grids:** job count is cities × languages × grid tiles; start with one city and low depth.

If geocoding is unavailable, use explicit city coordinates for non-grid campaigns.
For engine problems, consult [upstream](https://github.com/gosom/google-maps-scraper); for PRO CLI bugs,
use [this repository's issues](https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill/issues).

## Stop the engine and manage data

```bash
docker compose stop
docker compose start
```

`docker compose down` removes the container but retains named data volumes.
For an intentional full reset only, `docker compose down -v` also deletes stored job data.

Exports in `output/` are independent of the Docker volumes. Keep contacts, reports and `.env` out of commits.
See [limits and responsible use](README.md#limits-and-responsible-use) before larger runs.

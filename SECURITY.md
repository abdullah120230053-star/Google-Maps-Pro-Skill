# Security policy

This page tells you what to report, where to report it, and what belongs elsewhere.

## What to report

Report any way the kit could expose the engine, leak data or run code it should not. Examples: a
change that binds the API beyond `127.0.0.1`, a script that leaks `SCRAPER_API_KEY`, or a
command in `.claude/settings.json` that grants more than local access.

The kit binds the engine's API to `127.0.0.1` because the engine has no built-in authentication.
Do not expose port 8080 to a network without an authenticating proxy in front of it.

## Where to report

Use this repository's [Security tab](https://github.com/abdullah120230053-star/Google-Maps-Pro-Skill/security)
and private vulnerability reporting when enabled. If no private reporting channel is available, open
an issue requesting a private contact method without disclosing vulnerability details, contacts or credentials.

## Out of scope

- Bugs in the engine itself. Report those upstream to
  [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper).
- Problems that only occur after you expose the API to a network without an auth proxy.
- Google rate-limiting your IP. That is expected behavior, covered in [SETUP.md](SETUP.md).

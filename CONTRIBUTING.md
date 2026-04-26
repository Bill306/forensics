# Contributing

Thanks for your interest! This project is small and opinionated, so here's the gist of what's welcome and what isn't.

## Welcome

- **Bug fixes** — broken edge cases in ticker resolution, deploy issues on platforms other than Render, browser quirks in the UI
- **New exchanges** — extend `EXCHANGE_MAP` in `app.py` with proper TradingView prefix + yfinance suffix
- **Better skill examples** — improvements to the `example-stock-chart` placeholder so it's a clearer reference for new users
- **Documentation** — clarifying confusing parts of the README, adding deploy guides for other platforms
- **Translations** — README in other languages, particularly CN/JP/KR given the global ticker support

## Probably not welcome

- **A "real" forensic skill** in this repo. The whole point of the placeholder pattern is that proprietary research methodology stays out of the public repo. If you have a forensic skill you've open-sourced, link to it from the README — don't merge it in.
- **Major architectural changes** without an issue first. The 2-step blocking flow, shared-password auth, and 24h cache are deliberate choices.
- **Adding more frameworks.** No Next.js port, no streaming refactor, no DB integration. Keep it boring.

## Process

1. Open an issue describing the change
2. Wait for a reply confirming it's a fit before opening a PR
3. Keep PRs small and focused

## Local development

See the README's [Local development](README.md#local-development) section.

When testing changes to the SDK integration, use the placeholder skill — it's fast (a few seconds vs. minutes for a real research skill) and lets you iterate.

## Code style

- Python: standard `black` formatting, line length 100
- HTML/JS in templates: 2-space indent, no build step
- Don't introduce new dependencies without justification — the `requirements.txt` is short on purpose

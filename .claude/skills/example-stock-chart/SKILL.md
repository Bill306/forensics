---
name: example-stock-chart
description: Example skill showing the contract this app expects. Replace with your own skill (see README "Bring your own skill"). When invoked, reads stock metadata from the prompt and writes a minimal HTML chart to the path requested in the prompt.
---

# Example Stock Chart Skill

This is a **placeholder skill** that ships with the public repository. It demonstrates the contract that `app.py` expects:

1. The backend passes ticker metadata + a target output path in the prompt
2. The skill writes a self-contained HTML file to that exact path
3. The backend serves the file from `static/charts/`

This example produces a deliberately minimal chart (just current price + a "replace this skill" notice) so the app boots and shows something. It's not meant for actual analysis — replace it with your own.

## How the app calls this skill

When a user clicks "Generate", `app.py` runs Claude with a prompt like:

```
Run the {skill name} skill for NASDAQ:NVDA.

Pre-resolved metadata:
- Company: NVIDIA Corporation
- TradingView symbol: NASDAQ:NVDA
- yfinance symbol: NVDA
- Currency: USD
- Current price: 850.0
- 52w range: 400.0 to 974.0
- Market cap: 2100000000000

Required output path:
/path/to/static/charts/NASDAQ_NVDA_Forensic.html

Do all forensic event research yourself. Don't ask for confirmation.
```

## What this skill does

When triggered, this skill writes a minimal stub HTML file to the requested path. It does NOT do any forensic research — it's just enough to verify the SDK + skill plumbing works end-to-end.

The HTML it produces:
- Shows the company name and current price
- Embeds a TradingView widget for the symbol
- Has a banner explaining this is a placeholder

## Procedure

When asked to run for a ticker:

1. Parse the metadata from the prompt (company name, TradingView symbol, current price, output path)
2. Write a self-contained HTML file to the exact output path with the structure shown in `template.html`
3. Replace these tokens in the template before writing:
   - `{COMPANY_NAME}` → the company name from the prompt
   - `{TV_SYMBOL}` → the TradingView symbol (e.g. `NASDAQ:NVDA`)
   - `{CURRENT_PRICE}` → the current price
4. Done. Don't research events, don't pull historical data, don't do anything fancy.

The user will replace this with their real skill — see the repo README "Bring your own skill" section.

## Template structure

The template lives in `template.html` — a TradingView widget embed with a "Replace this skill" banner.

Read it, do the placeholder substitutions, write to the output path. That's the entire job.

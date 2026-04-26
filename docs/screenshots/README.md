# Screenshots

These SVG mockups show the four key states of the app:

1. **`01-search.svg`** — Landing page with masthead, ticker input, example chips, and recent charts list
2. **`02-preview.svg`** — Validation card after a ticker resolves (NVDA shown), with chart engine routing label
3. **`03-working.svg`** — "Claude is working" state with timer and stage cycling (Research → Data → Render)
4. **`04-chart.svg`** — Result view: the embedded forensic chart in an iframe (Samsung KRX:005930 example)

These are deliberately faithful to the actual app — same color tokens (`#0c1410`, `#d4a93e`), same fonts (Fraunces / JetBrains Mono / Inter), same spacing. Once you've deployed and run a real chart, you can replace these with PNG screenshots:

```bash
# After running the app locally:
# 1. Open http://localhost:8000 in Chrome
# 2. Use DevTools (F12) > Cmd-Shift-P > "Capture full size screenshot"
# 3. Save as docs/screenshots/01-search.png etc.
# 4. Update README image references from .svg to .png
```

GitHub renders SVG inline in markdown, so the current setup works without any extra steps.

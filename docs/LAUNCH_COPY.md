# Launch announcement copy

Pre-written copy for various platforms. Customize and fire.

---

## X / Twitter (long form, 280 chars limit per tweet)

### Single tweet version

> Open-sourced this weekend: type a stock ticker, get a forensic price chart with annotated catalysts. Built on Claude Agent SDK — the AI does the research, you ship the chart.
>
> 🔗 https://github.com/YOUR-USERNAME/forensic-stock-chart
>
> [attach 05-real-samsung-chart.png]

### Thread version

**1/**
> Spent the weekend turning my hedge-fund forensic chart workflow into an open-source app. Type a ticker, get a self-contained HTML chart with 15-25 catalysts pinned to the actual price line.
>
> Built on Claude Agent SDK. ~3 min per chart, ~$2 in API.
>
> [attach 05-real-samsung-chart.png]

**2/**
> The architecture is the interesting part: a tiny FastAPI app + a Claude Agent Skill that lives in `.claude/skills/`. The skill knows how to research events, pull yfinance data, generate the SVG chart.
>
> Swap the skill, get a different output. The app code never changes.

**3/**
> Why a skill not a prompt: a prompt is a request-time string. A skill is a folder with templates, references, procedures. It's the difference between "please do X" and "you know how to do X."
>
> For research-heavy work with proprietary methodology, skills are the right unit.

**4/**
> The placeholder skill in the public repo is intentionally minimal — just enough to verify the SDK plumbing. The README has a "Bring your own skill" section showing three patterns: commit it, fetch it from R2/S3 at deploy, or run local-only.
>
> Repo → https://github.com/YOUR-USERNAME/forensic-stock-chart

---

## Hacker News (Show HN)

**Title:** `Show HN: Type a ticker, get a forensic stock chart (Claude Agent SDK)`

**Body:**

> Hi HN, I built this over the weekend after using a manual version of the same workflow at my old job. The flow:
>
> 1. Enter any global stock ticker (NVDA, TSE:3563, KRX:005930, HKEX:9988, ...)
> 2. The app validates via yfinance and shows a preview card
> 3. Click "Generate" — Claude does ~3 min of forensic research, then writes a self-contained HTML chart
> 4. The chart shows weekly close price + 15-25 annotated events (scandals, earnings beats/misses, M&A, sell-side moves, narrative shifts) pinned to the actual price line
>
> Architecture is a thin FastAPI app + a Claude Agent Skill. The skill is the brain — knows the routing rule (US → TradingView embed, non-US → yfinance + custom SVG), the event taxonomy, the design tokens.
>
> Two interesting bits:
>
> - The repo only ships a placeholder skill. Your real skill stays private — there's a `scripts/fetch_skills.py` that pulls a tar.gz from R2/S3 at deploy time. Lets you open-source the app while keeping methodology private.
> - Per-session rate limiting (defaults: 10 charts/day, ~$30/day max API spend per user). Important because each chart is ~$1.50–3.
>
> Sample output (Samsung Electronics, the HBM-laggard-to-AI-anchor narrative):
> [link to docs/screenshots/05-real-samsung-chart.png]
>
> Repo: https://github.com/YOUR-USERNAME/forensic-stock-chart
>
> Happy to answer questions about the SDK integration or the skill design.

**Best post time:** Tuesday/Wednesday morning ET (~9-10am).

---

## /r/algotrading or /r/financialindependence

**Title:** I built a tool that turns any ticker into an annotated forensic chart

**Body:**

> Self-promotion warning: tool is open source, no paywall, no email gate. Just sharing because some of you might find it useful.
>
> What it does: enter a ticker, get an HTML chart with 15-25 annotated catalysts (scandals, earnings, M&A, sell-side moves) pinned to the actual price line. Works on US (live TradingView) and non-US (yfinance weekly bars). Each chart takes ~3 min and ~$2 of Claude API.
>
> Why I built it: I used to make these manually as part of every long/short pitch — each one took 2-3 hours of digging through 10-Ks, news archives, sell-side notes. Same template every time, just different data. Obvious automation candidate.
>
> [attach Samsung screenshot]
>
> The repo is the app + a placeholder skill. The "real" research skill is what I'm using on my own deploy and is kept separate (the README explains the pattern). You can drop in your own skill by editing one folder.
>
> Repo: https://github.com/YOUR-USERNAME/forensic-stock-chart
>
> Open to feedback.

---

## LinkedIn

**Headline:** Open-sourced a Claude Agent SDK weekend project: stock ticker in, forensic chart out

**Body:**

> 🔍 Open-sourced this weekend.
>
> The tool: type any global stock ticker (NVDA, Samsung, Sushiro, Alibaba HK...), get a self-contained HTML chart with 15-25 annotated catalysts pinned to the actual weekly price action. ~3 minutes, ~$2 of Claude API per chart.
>
> The interesting part isn't the chart — it's the architecture:
>
> ▸ FastAPI app in ~330 lines
> ▸ Claude Agent SDK invoking a "skill" (folder of templates + procedures)
> ▸ The skill is swappable — change methodology, change output, app code unchanged
>
> Skills are the unit of abstraction I've been waiting for since GPT-4. They're the difference between "stuff a 10K-token prompt every time" and "ship a coherent capability."
>
> Built it because I used to make these charts manually as a sell-side analyst — same template every time, just different data. Obvious automation candidate.
>
> Repo: https://github.com/YOUR-USERNAME/forensic-stock-chart
>
> Sample output below — Samsung Electronics, 2017 → today, the HBM-laggard-to-AI-anchor turn.

[attach 05-real-samsung-chart.png]

---

## Anthropic skills cookbook PR

The Anthropic skills cookbook lives at:
https://github.com/anthropics/claude-cookbooks (or the agent-skills repo, check current location)

Open a PR adding this as a referenced example:

**File:** new entry in the README's "Community examples" or "Showcase" section

**Content:**
```markdown
- **[forensic-stock-chart](https://github.com/YOUR-USERNAME/forensic-stock-chart)** — FastAPI app that turns a stock ticker into a forensic price chart with annotated events. Demonstrates the skill-as-pluggable-unit pattern with a private-bundle deploy mechanism. Real-world finance use case.
```

---

## WeChat / Chinese audience

If you have a CN audience, a 公众号 article would work well. Skeleton:

**Title:** 周末搞了个开源：输入股票代码，AI 帮你画一张带事件标注的 forensic chart

**Outline:**

1. 钩子：来一张 Samsung 的截图（"₩49,900 → ₩229,500，4×。每个事件都钉在真实价格上"）
2. 这是什么：app 演示 + 一句话讲清楚
3. 为啥值得讲：不是为了展示画图技术，是讲 **Claude Agent SDK + Skill** 这套新架构
   - "Skill" 不是 prompt — 它是一个可挂载的"能力包"
   - 应用代码 ≠ 知识。换 skill 换输出，app 不动
4. 我怎么用它：保持公开 repo 干净，私有 skill 通过 R2 signed URL 注入。开源 + 保密两不误
5. 给一些可以应用到其他场景的思路（不只是金融）
6. Repo 链接 + 自己 deploy 步骤

我可以单独帮你写完整的 公众号 草稿 — 告诉我就行。

---

## What to attach where

| Platform | Image |
|---|---|
| X/Twitter | `docs/screenshots/05-real-samsung-chart.png` (the real chart, max impact) |
| Hacker News | inline link to the GitHub-hosted PNG (HN doesn't render images inline) |
| Reddit | upload the Samsung PNG directly to the post |
| LinkedIn | the Samsung PNG |
| Anthropic cookbook | none needed; PR is text |

# Publishing to GitHub

A step-by-step checklist for shipping this repo publicly while keeping your private skill out of it.

> **Important:** Before you push, double-check `.gitignore` excludes `.claude/skills/*` (with an exception for `example-stock-chart`). The default `.gitignore` in this repo already does this. If you accidentally commit a private skill, see "Recovering from a leak" at the bottom.

---

## Pre-flight checklist

Run these in the repo root before `git push`:

```bash
# 1. Confirm only the placeholder skill is present
ls .claude/skills/
# Expected: only "example-stock-chart"
# If you see your real skill folder, MOVE IT OUT before continuing:
#   mv .claude/skills/forensic-price-chart ~/private-skills/

# 2. Confirm .gitignore is in effect
git check-ignore .claude/skills/forensic-price-chart 2>/dev/null && echo "✓ ignored" || echo "ℹ not present (good)"
git check-ignore .env 2>/dev/null && echo "✓ .env ignored"

# 3. Search for any leaked secrets
grep -rn "sk-ant-" --exclude-dir=.git --exclude-dir=.venv . | grep -v ".env.example"
grep -rn "APP_PASSWORD" --exclude-dir=.git --exclude-dir=.venv . | grep -v ".env.example" | grep -v "app.py"
# Both should print nothing.

# 4. Run a final dry run of git
git status
# Confirm no .env, no .claude/skills/<your real skill>, no static/charts/*.html
```

---

## Step 1 — Initialize the repo

```bash
cd /path/to/forensic-sdk-app
git init -b main
git add .
git status   # review what's about to be committed
```

Look at the file list carefully:
- ✓ `app.py`, `templates/`, `requirements.txt`, etc. — yes
- ✓ `.claude/skills/example-stock-chart/` — yes (the placeholder)
- ✓ `docs/screenshots/*.svg` — yes
- ✗ `.env` — should be missing
- ✗ `.claude/skills/forensic-price-chart/` — should be missing
- ✗ `static/charts/*.html` — should be missing (only `.gitkeep`)

If anything wrong appears, fix `.gitignore` and re-run.

```bash
git commit -m "Initial commit"
```

---

## Step 2 — Create the GitHub repo

### Option A — GitHub CLI (recommended)

```bash
# Public:
gh repo create forensic-stock-chart --public --source . --push --description "Type a ticker, get a forensic price chart. Built on Claude Agent SDK."

# Or private first, flip to public after you've confirmed everything looks right:
gh repo create forensic-stock-chart --private --source . --push
```

### Option B — Web UI

1. https://github.com/new
2. Repo name: `forensic-stock-chart`
3. Description: `Type a ticker, get a forensic price chart. Built on Claude Agent SDK.`
4. **Public** (or Private if you want to verify first)
5. Don't initialize with README (we have one)
6. Create
7. Then locally:
   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/forensic-stock-chart.git
   git push -u origin main
   ```

---

## Step 3 — Configure repo metadata

After the first push, on the GitHub repo page:

### Topics (helps discoverability)

Click ⚙ next to "About" → add topics:
- `claude-agent-sdk`
- `agent-skills`
- `fastapi`
- `stock-charts`
- `financial-analysis`
- `forensic-research`
- `python`

### About description

> Type a ticker, get a forensic price chart with annotated catalysts. Built on Claude Agent SDK.

### Social preview image

Use one of the screenshot SVGs converted to PNG. From the repo root:

```bash
# If you have rsvg-convert installed:
rsvg-convert -w 1280 -h 640 docs/screenshots/04-chart.svg > docs/social-preview.png

# Or ImageMagick:
convert -density 144 -background "#0c1410" docs/screenshots/04-chart.svg \
  -resize 1280x640 docs/social-preview.png
```

Then in repo Settings → General → Social preview → upload `docs/social-preview.png`.

---

## Step 4 — Deploy with your private skill (the bundle workflow)

The public repo only ships the `example-stock-chart` placeholder. To run the **real** forensic skill on your deployed instance, you host the skill somewhere private and have Render fetch it at build time via `SKILLS_BUNDLE_URL`.

This pattern is intentional: it keeps your repo open-sourceable while keeping your IP private.

### 4a — Make the bundle

From wherever you keep your private skill on disk:

```bash
# Your private skill lives somewhere outside the public repo, e.g.:
#   ~/private-skills/forensic-price-chart/
#     ├── SKILL.md
#     ├── references/
#     └── assets/

cd ~/private-skills
tar czf forensic-skills-bundle.tar.gz forensic-price-chart/
ls -la forensic-skills-bundle.tar.gz   # should be ~25-50 KB
```

Verify the contents:

```bash
tar tzf forensic-skills-bundle.tar.gz
# Expected output:
#   forensic-price-chart/
#   forensic-price-chart/SKILL.md
#   forensic-price-chart/references/...
#   forensic-price-chart/assets/...
```

### 4b — Host the bundle

Pick **one** of these. Cloudflare R2 is recommended — free tier covers this use case, signed URLs are easy to refresh.

#### Option A — Cloudflare R2 (recommended)

```bash
# One-time setup: install wrangler if you don't have it
npm install -g wrangler
wrangler login

# Create a bucket (one-time)
wrangler r2 bucket create forensic-private-bundles

# Upload the bundle
wrangler r2 object put forensic-private-bundles/forensic-skills-bundle.tar.gz \
  --file forensic-skills-bundle.tar.gz

# Generate a signed URL valid for 7 days
# (Or use the dashboard: R2 → bucket → object → "Create presigned URL")
```

Copy the resulting signed URL. It looks like:
```
https://<account>.r2.cloudflarestorage.com/forensic-private-bundles/forensic-skills-bundle.tar.gz?X-Amz-...
```

Refresh the URL whenever it expires (or set a longer TTL).

#### Option B — AWS S3

```bash
aws s3 cp forensic-skills-bundle.tar.gz s3://your-private-bucket/
aws s3 presign s3://your-private-bucket/forensic-skills-bundle.tar.gz --expires-in 604800
# → copy the signed URL
```

#### Option C — Private GitHub release asset

```bash
# Make a separate PRIVATE repo (e.g. "forensic-skills-private")
gh repo create forensic-skills-private --private
gh release create v1.0 --repo forensic-skills-private \
  forensic-skills-bundle.tar.gz

# Get the asset's API URL:
gh release view v1.0 --repo forensic-skills-private --json assets \
  --jq '.assets[0].apiUrl'
# → https://api.github.com/repos/YOU/forensic-skills-private/releases/assets/<id>
```

For this option you also need a fine-grained PAT with read access to that repo. Generate at https://github.com/settings/personal-access-tokens (or use a classic PAT with `repo` scope). Set `SKILLS_BUNDLE_TOKEN` in Render to that PAT.

### 4c — Wire it up on Render

In your Render dashboard for this service, **Environment** tab:

| Key | Value | Notes |
|---|---|---|
| `SKILLS_BUNDLE_URL` | `https://...your.signed.url...` | Hidden value, sync: false |
| `SKILLS_BUNDLE_TOKEN` | `ghp_...` | Only if Option C; leave empty for R2/S3 signed URLs |
| `SKILL_NAME` | `forensic-price-chart` | The skill folder name inside your bundle |

### 4d — Trigger a redeploy

In Render dashboard: **Manual Deploy** → **Deploy latest commit**.

Watch the build log. You should see:

```
⤓ Fetching skills bundle from: https://...
✓ Downloaded 26.3 KB
✓ Skills now installed in /opt/render/.../.claude/skills:
    · example-stock-chart (4.9 KB)
    · forensic-price-chart (83.3 KB)
```

After deploy, the placeholder banner should disappear and `/api/limits` should return `"skill": "forensic-price-chart"` and `"is_placeholder": false`.

### 4e — Updating the skill later

Edit your private skill on disk → re-tar → re-upload to R2/S3 (overwrite same key) → redeploy on Render. The signed URL stays the same; only the bundle contents change.

```bash
# Quick update flow:
cd ~/private-skills
# (make your edits)
tar czf forensic-skills-bundle.tar.gz forensic-price-chart/
wrangler r2 object put forensic-private-bundles/forensic-skills-bundle.tar.gz \
  --file forensic-skills-bundle.tar.gz
# Then in Render dashboard: Manual Deploy
```

---

## Step 5 — First release

Cut a v0.1.0 release so anyone can `git checkout v0.1.0` to a known-good state.

```bash
git tag -a v0.1.0 -m "v0.1.0 — initial public release"
git push origin v0.1.0
```

Then on GitHub: **Releases** → **Draft a new release** → choose tag `v0.1.0`.

**Title:** `v0.1.0 — Initial release`

**Description (copy-paste):**

```markdown
First public release.

## What's in the box

- FastAPI backend that resolves global stock tickers (US, HK, JP, KR, EU, ...)
- 2-step UI: search → preview → generate → chart
- Shared-password auth + per-session rate limiting
- 24h cache + persistent disk on Render
- Render Blueprint for one-click deploy
- Placeholder `example-stock-chart` skill demonstrating the contract
- `scripts/fetch_skills.py` for injecting private skills at deploy time

## Quick start

See the [README](https://github.com/YOUR-USERNAME/forensic-stock-chart#quick-deploy-to-render) for deploy instructions.

## What's not included

The real `forensic-price-chart` skill that produces the screenshots is a separate project — see ["Bring your own skill"](https://github.com/YOUR-USERNAME/forensic-stock-chart#bring-your-own-skill) in the README to wire up your own.
```

---

## Step 6 — Promote (optional)

If you want eyes on it:

- **Hacker News** — title: `Show HN: Type a ticker, get a forensic price chart (Claude Agent SDK)`. Best posted Tue–Thu morning ET.
- **/r/algotrading** or **/r/finance** — softer angle: "I built a tool that..."
- **X/Twitter** — `@AnthropicAI` reposts good Agent SDK examples. Tag them.
- **Anthropic skills cookbook** — open a PR to https://github.com/anthropics/claude-cookbooks adding this as an example
- **Awesome lists** — `awesome-claude-agent-sdk` and similar

---

## Recovering from a leak

If you accidentally committed something secret:

```bash
# 1. STOP. Do NOT just delete and re-commit. The blob lives in git history.
# 2. Use git-filter-repo to scrub it from all history:
pip install git-filter-repo
git filter-repo --path .claude/skills/forensic-price-chart --invert-paths

# 3. Force push (this rewrites history; coordinate with anyone who cloned):
git push --force origin main

# 4. Rotate any credentials that were in the leaked content
```

If a skill leaked, treat it like an API key leak: rotate (i.e. consider the methodology now public knowledge for anyone who saw it during the window).

---

## Maintenance after launch

- **Watch issues.** First PRs are usually about ticker formats / new exchanges — easy merges
- **Don't merge "real" skills.** Per CONTRIBUTING.md, skill PRs go to separate repos
- **Bump dependencies quarterly.** `claude-agent-sdk` is the one most likely to need updates
- **Refresh screenshots after major UI changes**

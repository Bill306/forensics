#!/usr/bin/env bash
#
# publish-to-github.sh
# ====================
# Walks you through publishing forensic-sdk-app to GitHub with safety checks.
# Designed so a careful first-time user can't accidentally leak their private skill.
#
# Prerequisites (one-time, ~5 minutes):
#   1. Install GitHub CLI:  https://cli.github.com  (or `brew install gh` on macOS)
#   2. Authenticate:        gh auth login
#   3. Install git:         (already installed if you have gh)
#
# Usage:
#   bash publish-to-github.sh
#
# What this does:
#   1. Verifies you have the prerequisites
#   2. Asks for a repo name
#   3. Checks the working tree for leaked secrets and private skills
#   4. Initializes git, makes the first commit
#   5. Creates a PRIVATE GitHub repo first (you can flip to public after review)
#   6. Sets repo description + topics
#   7. Prints next steps for Render deploy
#
# This script never modifies anything OUTSIDE the current directory.

set -euo pipefail

# ---- Pretty output ----
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*"; }
step()  { echo; echo -e "${BLUE}${BOLD}▸ $*${NC}"; }
ask()   { echo -en "${YELLOW}?${NC} $* "; }

abort() {
  err "$1"
  echo
  echo "Aborted. Nothing was pushed."
  exit 1
}

# ============================================================
# Step 0 — Verify we're in the right directory
# ============================================================
step "Verifying current directory"

if [[ ! -f app.py ]] || [[ ! -d .claude/skills ]]; then
  abort "This script must be run from inside the forensic-sdk-app directory.
       Expected files: app.py, .claude/skills/
       Currently in: $(pwd)"
fi
ok "Looks like a forensic-sdk-app directory"

# ============================================================
# Step 1 — Verify prerequisites
# ============================================================
step "Checking prerequisites"

if ! command -v git &> /dev/null; then
  abort "git not found. Install from https://git-scm.com"
fi
ok "git: $(git --version)"

if ! command -v gh &> /dev/null; then
  abort "GitHub CLI (gh) not found.
       Install from https://cli.github.com  (or 'brew install gh' on macOS)"
fi
ok "gh: $(gh --version | head -1)"

if ! gh auth status &> /dev/null; then
  abort "Not authenticated with GitHub.
       Run: gh auth login
       Then re-run this script."
fi
GH_USER=$(gh api user --jq .login)
ok "Authenticated as: ${BOLD}$GH_USER${NC}"

# ============================================================
# Step 2 — Safety: scan for leaked content
# ============================================================
step "Scanning working tree for leaked secrets / private skills"

LEAKS_FOUND=0

# 2a. Check for any skill folders besides example-stock-chart
echo "  Skills present in .claude/skills/:"
for dir in .claude/skills/*/; do
  [[ -d "$dir" ]] || continue
  name=$(basename "$dir")
  if [[ "$name" == "example-stock-chart" ]]; then
    echo -e "    ${GREEN}✓${NC} $name (placeholder, ok to commit)"
  else
    echo -e "    ${RED}✗${NC} $name (not the placeholder!)"
    LEAKS_FOUND=$((LEAKS_FOUND + 1))
    LEAKED_SKILL="$name"
  fi
done

# 2b. Check for .env file (shouldn't be committed)
if [[ -f .env ]]; then
  warn ".env file present — will be excluded by .gitignore but verify"
  if grep -q "^.env$" .gitignore 2>/dev/null || grep -q "^\.env$" .gitignore 2>/dev/null; then
    ok ".env is .gitignored"
  else
    err ".env is NOT in .gitignore — STOP and fix"
    LEAKS_FOUND=$((LEAKS_FOUND + 1))
  fi
fi

# 2c. Scan all tracked-eligible files for API keys
SCAN_RESULTS=$(grep -rEn "sk-ant-[a-zA-Z0-9_-]{20,}" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__ \
  --exclude="*.example" \
  . 2>/dev/null || true)
if [[ -n "$SCAN_RESULTS" ]]; then
  err "Possible API key leak detected:"
  echo "$SCAN_RESULTS"
  LEAKS_FOUND=$((LEAKS_FOUND + 1))
else
  ok "No API key patterns found in source files"
fi

# 2d. Scan for hardcoded passwords
PWD_RESULTS=$(grep -rEn 'APP_PASSWORD\s*=\s*"[^"]+"' \
  --exclude-dir=.git --exclude-dir=.venv \
  --exclude="*.example" --exclude="*.md" \
  . 2>/dev/null | grep -v 'os.getenv' | grep -v 'getenv' || true)
if [[ -n "$PWD_RESULTS" ]]; then
  err "Possible hardcoded password:"
  echo "$PWD_RESULTS"
  LEAKS_FOUND=$((LEAKS_FOUND + 1))
else
  ok "No hardcoded passwords found"
fi

# 2e. Final verdict
if [[ $LEAKS_FOUND -gt 0 ]]; then
  echo
  err "Found $LEAKS_FOUND issue(s). Cannot proceed."
  echo
  if [[ -n "${LEAKED_SKILL:-}" ]]; then
    echo "To remove the private skill:"
    echo "  mv .claude/skills/$LEAKED_SKILL ~/private-skills/"
    echo "Then re-run this script."
  fi
  exit 1
fi
ok "Pre-flight scan passed"

# ============================================================
# Step 3 — Get repo configuration from user
# ============================================================
step "Repo configuration"

ask "Repository name:"
read -r REPO_NAME
REPO_NAME="${REPO_NAME// /-}"  # spaces to dashes
if [[ -z "$REPO_NAME" ]]; then
  abort "Repo name cannot be empty"
fi
if [[ ! "$REPO_NAME" =~ ^[a-zA-Z0-9_.-]+$ ]]; then
  abort "Invalid repo name. Use only letters, numbers, dashes, underscores, dots."
fi

DEFAULT_DESC="Type a stock ticker, get a forensic price chart with annotated catalysts. Built on Claude Agent SDK."
ask "Description (or Enter for default):"
read -r REPO_DESC
REPO_DESC="${REPO_DESC:-$DEFAULT_DESC}"

echo
echo "${BOLD}Visibility:${NC}"
echo "  ${GREEN}1) PRIVATE${NC} (recommended — let you verify everything looks right, then flip public on github.com)"
echo "  2) PUBLIC (commit straight to public)"
ask "Choice [1]:"
read -r VIS_CHOICE
VIS_CHOICE="${VIS_CHOICE:-1}"
if [[ "$VIS_CHOICE" == "2" ]]; then
  VISIBILITY="--public"
  VIS_LABEL="public"
else
  VISIBILITY="--private"
  VIS_LABEL="private"
fi

echo
echo "${BOLD}Summary:${NC}"
echo "  GitHub user: $GH_USER"
echo "  Repo name:   $GH_USER/$REPO_NAME"
echo "  Visibility:  $VIS_LABEL"
echo "  Description: $REPO_DESC"
echo
ask "Proceed? [y/N]:"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  abort "Cancelled by user"
fi

# ============================================================
# Step 4 — Init git + first commit
# ============================================================
step "Initializing git repository"

if [[ -d .git ]]; then
  warn ".git directory already exists — using existing repo"
else
  git init -b main &> /dev/null
  ok "git init"
fi

git add .

# Show what's staged
echo
echo "Files about to be committed:"
git status --short | head -40
TOTAL_FILES=$(git status --short | wc -l | tr -d ' ')
if [[ $TOTAL_FILES -gt 40 ]]; then
  echo "  ... and $((TOTAL_FILES - 40)) more"
fi

# Critical re-check: list ALL staged files, look for forbidden patterns
echo
echo "Verifying no private content is staged..."
STAGED=$(git diff --cached --name-only)

# Re-check for skill folders
STAGED_SKILLS=$(echo "$STAGED" | grep -E "^\.claude/skills/" | awk -F/ '{print $3}' | sort -u || true)
for s in $STAGED_SKILLS; do
  if [[ "$s" != "example-stock-chart" ]] && [[ -n "$s" ]]; then
    abort "About to commit private skill: .claude/skills/$s
       This shouldn't happen if .gitignore is correct.
       Inspect with: cat .gitignore"
  fi
done
ok "Only the example-stock-chart skill is staged"

# Re-check no .env
if echo "$STAGED" | grep -qx ".env"; then
  abort ".env is about to be committed!
       Run: git rm --cached .env
       Then verify .gitignore has '.env' on its own line."
fi
ok ".env is not staged"

# Re-check no generated charts
GENERATED_CHARTS=$(echo "$STAGED" | grep -E "^static/charts/.*\.html$" || true)
if [[ -n "$GENERATED_CHARTS" ]]; then
  abort "About to commit generated chart files:
$GENERATED_CHARTS"
fi
ok "No generated charts are staged"

echo
ask "All checks passed. Make the initial commit? [Y/n]:"
read -r DO_COMMIT
if [[ "$DO_COMMIT" =~ ^[Nn]$ ]]; then
  abort "Cancelled before commit"
fi

git commit -q -m "Initial commit"
ok "Initial commit created"

# ============================================================
# Step 5 — Create GitHub repo + push
# ============================================================
step "Creating GitHub repo and pushing"

# Check if remote 'origin' already exists (re-running script)
if git remote get-url origin &> /dev/null; then
  warn "remote 'origin' already configured: $(git remote get-url origin)"
  ask "Use existing remote? [Y/n]:"
  read -r USE_EXISTING
  if [[ ! "$USE_EXISTING" =~ ^[Nn]$ ]]; then
    git push -u origin main
    REPO_URL=$(git remote get-url origin)
    ok "Pushed to existing remote"
  else
    abort "Refusing to overwrite existing remote. Remove it manually with: git remote remove origin"
  fi
else
  echo "Creating $VIS_LABEL repo $GH_USER/$REPO_NAME ..."
  gh repo create "$REPO_NAME" $VISIBILITY \
    --source . \
    --push \
    --description "$REPO_DESC"
  REPO_URL="https://github.com/$GH_USER/$REPO_NAME"
  ok "Repo created and pushed: $REPO_URL"
fi

# ============================================================
# Step 6 — Configure repo metadata
# ============================================================
step "Setting repo topics"

gh repo edit "$GH_USER/$REPO_NAME" \
  --add-topic claude-agent-sdk \
  --add-topic agent-skills \
  --add-topic fastapi \
  --add-topic stock-charts \
  --add-topic financial-analysis \
  --add-topic forensic-research \
  --add-topic python \
  &> /dev/null
ok "Topics added: claude-agent-sdk, agent-skills, fastapi, stock-charts, financial-analysis, forensic-research, python"

# ============================================================
# Done
# ============================================================
echo
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}✓ GitHub publish complete${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "Repo URL:  $REPO_URL"
echo
echo -e "${BOLD}Next steps:${NC}"
echo
echo "  1. Open the repo and verify everything looks right:"
echo "     ${BLUE}gh repo view --web${NC}"
echo
echo "  2. Upload the social preview image:"
echo "     - Go to Settings → General → Social preview"
echo "     - Upload docs/social-preview.png"
echo

if [[ "$VIS_LABEL" == "private" ]]; then
  echo "  3. (Optional) Make the repo public after review:"
  echo "     ${BLUE}gh repo edit $GH_USER/$REPO_NAME --visibility public${NC}"
  echo "     (or via the website: Settings → Danger Zone)"
  echo
fi

echo "  4. Deploy to Render:"
echo "     - Sign up at https://render.com"
echo "     - New + → Blueprint → connect this repo"
echo "     - Set environment variables (see PUBLISHING.md Step 4):"
echo "         ANTHROPIC_API_KEY"
echo "         APP_PASSWORD"
echo "         SKILLS_BUNDLE_URL  (for your private skill)"
echo "         SKILL_NAME=forensic-price-chart"
echo
echo "  5. (After deploy works) Cut a v0.1.0 release:"
echo "     ${BLUE}git tag -a v0.1.0 -m 'Initial release' && git push origin v0.1.0${NC}"
echo "     Then: gh release create v0.1.0 --generate-notes"
echo
echo "  6. Promote (optional): see docs/LAUNCH_COPY.md for ready-to-paste copy"
echo
echo "Full step-by-step guide is in: PUBLISHING.md"
echo

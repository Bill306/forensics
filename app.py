"""
Forensic Stock Chart - FastAPI + Claude Agent SDK
With shared-password auth + rate limiting.

Environment:
  ANTHROPIC_API_KEY      - required, your API key
  APP_PASSWORD           - required, shared password for the app
  APP_SECRET_KEY         - required, used to sign auth cookies (generate with `openssl rand -hex 32`)
  RATE_LIMIT_GENERATE    - optional, e.g. "10/day" (default)
  RATE_LIMIT_RESOLVE     - optional, e.g. "30/minute" (default)

Two-step flow:
  1. POST /api/resolve   - validate ticker, return preview metadata
  2. POST /api/generate  - run Claude with the skill, return chart URL when done

All /api/* endpoints (except /api/login) require auth.
"""

import os
import re
import secrets
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import yfinance as yf

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from claude_agent_sdk import query, ClaudeAgentOptions

# ---- Paths ----
BASE_DIR = Path(__file__).parent.absolute()
STATIC_DIR = BASE_DIR / "static"
CHARTS_DIR = STATIC_DIR / "charts"
TEMPLATES_DIR = BASE_DIR / "templates"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ---- Config ----
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "")

if not APP_PASSWORD:
    print("⚠ WARNING: APP_PASSWORD not set. App will be inaccessible. Set APP_PASSWORD env var.")
if not APP_SECRET_KEY:
    APP_SECRET_KEY = secrets.token_hex(32)
    print("⚠ WARNING: APP_SECRET_KEY not set. Generated a temporary one — cookies will invalidate on restart.")

RATE_LIMIT_GENERATE = os.getenv("RATE_LIMIT_GENERATE", "10/day")
RATE_LIMIT_RESOLVE = os.getenv("RATE_LIMIT_RESOLVE", "30/minute")

# Which skill the SDK should invoke. Defaults to the example shipped with the public repo.
# Set this to your private skill name when deploying with a real skill.
SKILL_NAME = os.getenv("SKILL_NAME", "example-stock-chart")

COOKIE_NAME = "forensic_auth"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
signer = URLSafeTimedSerializer(APP_SECRET_KEY, salt="forensic-auth")


# ---- Rate limiter ----
def rate_limit_key(request: Request) -> str:
    """Rate limit by authenticated session if logged in, else by IP."""
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        try:
            data = signer.loads(cookie, max_age=COOKIE_MAX_AGE)
            return f"session:{data}"
        except (BadSignature, SignatureExpired):
            pass
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=rate_limit_key)

# ---- App ----
app = FastAPI(title="Forensic Stock Chart")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ============================================================
# Auth
# ============================================================

def is_authed(request: Request) -> bool:
    if not APP_PASSWORD:
        return False
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return False
    try:
        signer.loads(cookie, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_auth(request: Request):
    """FastAPI dependency: 401 if not authed."""
    if not is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    if is_authed(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if not APP_PASSWORD:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Server misconfigured: APP_PASSWORD not set"},
            status_code=500
        )

    if not secrets.compare_digest(password, APP_PASSWORD):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Wrong password"},
            status_code=401
        )

    session_id = secrets.token_hex(16)
    signed = signer.dumps(session_id)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=signed,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.post("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# ============================================================
# Ticker resolution
# ============================================================

EXCHANGE_MAP = {
    "TSE":      (".T",  "TSE",      "Tokyo"),
    "HKEX":     (".HK", "HKEX",     "Hong Kong"),
    "HKG":      (".HK", "HKEX",     "Hong Kong"),
    "SSE":      (".SS", "SSE",      "Shanghai"),
    "SZSE":     (".SZ", "SZSE",     "Shenzhen"),
    "KRX":      (".KS", "KRX",      "Korea"),
    "KOSPI":    (".KS", "KRX",      "Korea"),
    "KOSDAQ":   (".KQ", "KRX",      "Korea (KOSDAQ)"),
    "TWSE":     (".TW", "TWSE",     "Taiwan"),
    "LSE":      (".L",  "LSE",      "London"),
    "EURONEXT": (".PA", "EURONEXT", "Paris"),
    "XETR":     (".DE", "XETR",     "Frankfurt"),
    "ASX":      (".AX", "ASX",      "Sydney"),
    "TSX":      (".TO", "TSX",      "Toronto"),
    "NYSE":     ("",    "NYSE",     "New York (NYSE)"),
    "NASDAQ":   ("",    "NASDAQ",   "New York (NASDAQ)"),
}


class TickerResolution(BaseModel):
    raw_input: str
    is_us: bool
    yfinance_symbol: str
    tradingview_symbol: str
    market: str
    company_name: str | None = None
    current_price: float | None = None
    currency: str | None = None
    market_cap: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    error: str | None = None


def resolve_ticker(raw: str) -> TickerResolution:
    raw = raw.strip().upper()
    if not raw:
        return TickerResolution(
            raw_input=raw, is_us=False, yfinance_symbol="",
            tradingview_symbol="", market="", error="Empty ticker"
        )

    if ":" in raw:
        prefix, ticker = raw.split(":", 1)
        if prefix not in EXCHANGE_MAP:
            return TickerResolution(
                raw_input=raw, is_us=False, yfinance_symbol="",
                tradingview_symbol="", market="",
                error=f"Unknown exchange prefix '{prefix}'. Try TSE, HKEX, KRX, SSE, SZSE, LSE, NYSE, NASDAQ..."
            )
        yf_suffix, tv_prefix, market = EXCHANGE_MAP[prefix]
        is_us = prefix in ("NYSE", "NASDAQ")
        yf_symbol = ticker if is_us else f"{ticker}{yf_suffix}"
        return TickerResolution(
            raw_input=raw, is_us=is_us, yfinance_symbol=yf_symbol,
            tradingview_symbol=f"{tv_prefix}:{ticker}", market=market,
        )

    if raw.isdigit():
        return TickerResolution(
            raw_input=raw, is_us=False, yfinance_symbol="",
            tradingview_symbol="", market="",
            error=f"Numeric ticker '{raw}' is ambiguous. Try HKEX:{raw}, KRX:{raw}, TSE:{raw}, etc."
        )

    return TickerResolution(
        raw_input=raw, is_us=True, yfinance_symbol=raw,
        tradingview_symbol=f"NASDAQ:{raw}", market="US",
    )


def enrich_with_yfinance(res: TickerResolution) -> TickerResolution:
    try:
        t = yf.Ticker(res.yfinance_symbol)
        info = t.info or {}
        if not info or info.get("regularMarketPrice") is None:
            res.error = f"No data for '{res.yfinance_symbol}'. Check the ticker."
            return res

        res.company_name = info.get("longName") or info.get("shortName")
        res.current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        res.currency = info.get("currency", "USD")
        res.market_cap = info.get("marketCap")
        res.week_52_high = info.get("fiftyTwoWeekHigh")
        res.week_52_low = info.get("fiftyTwoWeekLow")

        if res.is_us:
            ex = (info.get("exchange") or "").upper()
            if "NYS" in ex or "NYSE" in ex:
                res.tradingview_symbol = f"NYSE:{res.yfinance_symbol}"
            elif "NMS" in ex or "NAS" in ex:
                res.tradingview_symbol = f"NASDAQ:{res.yfinance_symbol}"
    except Exception as e:
        res.error = f"yfinance lookup failed: {e}"
    return res


# ============================================================
# Routes — main app (auth required)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not is_authed(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthz")
async def healthz():
    """Health check — no auth required so Render can probe it."""
    return {"ok": True}


class ResolveBody(BaseModel):
    ticker: str


@app.post("/api/resolve", dependencies=[Depends(require_auth)])
@limiter.limit(RATE_LIMIT_RESOLVE)
async def api_resolve(request: Request, body: ResolveBody):
    """Step 1: validate the ticker, return preview metadata."""
    res = resolve_ticker(body.ticker)
    if res.error:
        return res
    res = enrich_with_yfinance(res)
    return res


class GenerateBody(BaseModel):
    ticker: str


@app.post("/api/generate", dependencies=[Depends(require_auth)])
@limiter.limit(RATE_LIMIT_GENERATE)
async def api_generate(request: Request, body: GenerateBody):
    """Step 2: run Claude with the forensic-price-chart skill."""
    res = resolve_ticker(body.ticker)
    if res.error:
        raise HTTPException(400, res.error)
    res = enrich_with_yfinance(res)
    if res.error:
        raise HTTPException(400, res.error)

    file_safe = re.sub(r"[^A-Za-z0-9_]", "_", res.tradingview_symbol)
    output_filename = f"{file_safe}_Forensic.html"
    output_path = CHARTS_DIR / output_filename

    # Cache: serve existing chart if < 24h old
    if output_path.exists():
        age_hours = (datetime.now().timestamp() - output_path.stat().st_mtime) / 3600
        if age_hours < 24:
            return {
                "url": f"/static/charts/{output_filename}",
                "filename": output_filename,
                "size_kb": round(output_path.stat().st_size / 1024, 1),
                "cached": True,
                "cache_age_hours": round(age_hours, 1),
            }

    prompt = f"""Run the {SKILL_NAME} skill for {res.tradingview_symbol}.

Pre-resolved metadata (use these — do not re-fetch):
- Company: {res.company_name}
- TradingView symbol: {res.tradingview_symbol}
- yfinance symbol: {res.yfinance_symbol}
- Market: {res.market}
- Currency: {res.currency}
- Current price: {res.current_price}
- 52w range: {res.week_52_low} to {res.week_52_high}
- Market cap: {res.market_cap}
- Is US listing: {res.is_us}

Required output path (write the final HTML to exactly this path):
{output_path}

Do whatever research the skill prescribes. Don't ask for confirmation, just produce the file. Be efficient — don't re-fetch metadata I already gave you above.
"""

    options = ClaudeAgentOptions(
        cwd=str(BASE_DIR),
        setting_sources=["project"],
        allowed_tools=["Skill", "Read", "Write", "Bash", "WebSearch", "WebFetch", "Grep", "Glob"],
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": "You are running inside a web app backend. Trigger the forensic-price-chart skill, produce the requested output file, and stop. No long explanations.",
        },
        max_turns=80,
    )

    try:
        async for _ in query(prompt=prompt, options=options):
            pass
    except Exception as e:
        raise HTTPException(500, f"Claude run failed: {e}")

    if not output_path.exists():
        raise HTTPException(500, "Claude finished but did not produce the expected file. Try again.")

    size_kb = output_path.stat().st_size / 1024
    return {
        "url": f"/static/charts/{output_filename}",
        "filename": output_filename,
        "size_kb": round(size_kb, 1),
        "cached": False,
    }


@app.get("/api/recent", dependencies=[Depends(require_auth)])
async def api_recent():
    files = sorted(CHARTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    return [{
        "filename": f.name,
        "url": f"/static/charts/{f.name}",
        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        "size_kb": round(f.stat().st_size / 1024, 1),
    } for f in files]


@app.get("/api/limits", dependencies=[Depends(require_auth)])
async def api_limits():
    """Expose the configured rate limits and active skill to the front-end."""
    return {
        "generate": RATE_LIMIT_GENERATE,
        "resolve": RATE_LIMIT_RESOLVE,
        "skill": SKILL_NAME,
        "is_placeholder": SKILL_NAME == "example-stock-chart",
    }


# ---- Entry ----
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

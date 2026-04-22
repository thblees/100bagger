"""
Quality overlay filters for the 100-bagger screener.

Runs AFTER the base hard filter and scoring. Distinguishes 'real operational
quality' from 'statistical artefacts' (e.g. one-time license payments that
spike a single quarter's EPS).

Five quality gates (all must pass):
  Q1: TTM EPS positive (not just MRQ) — rules out fresh turnarounds whose score
      is driven by a single positive quarter following losses.
  Q2: Operating cash flow positive in the most recent available period — earnings
      backed by real cash, not accounting-only.
  Q3: Share count growth under 20% yoy — rules out severe dilution (= financing
      distress).
  Q4: Market cap >= 50 Mio USD — ultra-micro-caps below 50M have chronic data
      quality problems and are nearly untradeable.
  Q5: Gross margin trend stable or rising over the last 4 quarters — the
      business is not being 'run into the ground' to chase revenue.
"""
from typing import Optional, Tuple, List
import yfinance as yf
import pandas as pd

MIN_MARKET_CAP_USD = 50_000_000
MAX_SHARE_GROWTH_YOY = 0.20  # 20%
MIN_GROSS_MARGIN_QUARTERS = 4


def _ocf_positive(ticker_obj: yf.Ticker) -> Optional[bool]:
    """Returns True if the most recent quarterly OCF is positive,
    None if the data is missing."""
    try:
        cf = ticker_obj.quarterly_cashflow
    except Exception:
        return None
    if cf is None or cf.empty:
        return None
    for row_name in ("Operating Cash Flow", "Total Cash From Operating Activities"):
        if row_name in cf.index:
            series = cf.loc[row_name].dropna()
            if series.empty:
                return None
            latest = series.iloc[0]  # columns are newest first
            return bool(float(latest) > 0)
    return None


def _share_growth_yoy(ticker_obj: yf.Ticker) -> Optional[float]:
    """Returns yoy growth in shares outstanding as a fraction (0.25 = 25%),
    or None if history is missing."""
    try:
        history = ticker_obj.get_shares_full(start="2024-01-01")
    except Exception:
        history = None
    if history is None or len(history) < 2:
        return None
    try:
        history = history.sort_index()
        latest = float(history.iloc[-1])
        # Find a data point ~1 year ago
        one_year_ago = history.index[-1] - pd.Timedelta(days=365)
        prior_slice = history[history.index <= one_year_ago]
        if prior_slice.empty:
            return None
        prior = float(prior_slice.iloc[-1])
        if prior <= 0:
            return None
        return (latest - prior) / prior
    except Exception:
        return None


def _gross_margin_stable_or_rising(ticker_obj: yf.Ticker) -> Optional[bool]:
    """Returns True if gross margin over the last 4 quarters is not in a clear
    decline. 'Clear decline' = last margin is more than 5 percentage points
    below the 4-quarter average."""
    try:
        income = ticker_obj.quarterly_income_stmt
    except Exception:
        return None
    if income is None or income.empty:
        return None

    revenue_row = None
    cogs_row = None
    for name in ("Total Revenue", "Operating Revenue"):
        if name in income.index:
            revenue_row = income.loc[name]
            break
    for name in ("Cost Of Revenue", "Cost of Revenue", "Cost of Goods Sold"):
        if name in income.index:
            cogs_row = income.loc[name]
            break

    if revenue_row is None or cogs_row is None:
        # Some business models (pure software, asset managers) report no COGS.
        # Treat as 'pass' — margin filter doesn't apply.
        return True

    quarters = revenue_row.index.sort_values(ascending=False).tolist()[:MIN_GROSS_MARGIN_QUARTERS]
    margins = []
    for q in quarters:
        rev = revenue_row.get(q)
        cogs = cogs_row.get(q)
        if pd.isna(rev) or pd.isna(cogs) or rev == 0:
            continue
        margins.append((float(rev) - float(cogs)) / float(rev))
    if len(margins) < 2:
        return None
    avg = sum(margins) / len(margins)
    latest = margins[0]
    return latest >= (avg - 0.05)  # allow 5pp drop from average


def quality_pass(row: dict) -> Tuple[bool, List[str]]:
    """Run all 5 quality gates on a scored company row.

    Input `row` is one entry from data.json 'top_results' (must contain at
    minimum: ticker, ttm_eps, market_cap_usd).

    Returns (passed_all: bool, reasons_for_failure: List[str]).
    Unknown/missing data is treated as a failure with reason prefix 'data:'.
    """
    reasons: List[str] = []
    ticker = row["ticker"]

    # Q1: TTM EPS positive
    if not (row.get("ttm_eps") is not None and row["ttm_eps"] > 0):
        reasons.append("Q1:ttm_eps_nonpositive")

    # Q4: Market Cap >= 50M
    if row.get("market_cap_usd", 0) < MIN_MARKET_CAP_USD:
        reasons.append("Q4:market_cap_too_small")

    # For Q2/Q3/Q5 we need live yfinance lookups
    try:
        t = yf.Ticker(ticker)
    except Exception:
        reasons.append("data:ticker_init_failed")
        return (False, reasons)

    # Q2: Operating Cash Flow positive
    ocf_ok = _ocf_positive(t)
    if ocf_ok is None:
        reasons.append("data:ocf_unknown")
    elif not ocf_ok:
        reasons.append("Q2:ocf_negative")

    # Q3: Share count growth < 20%
    share_growth = _share_growth_yoy(t)
    if share_growth is None:
        reasons.append("data:share_history_unknown")
    elif share_growth > MAX_SHARE_GROWTH_YOY:
        reasons.append(f"Q3:dilution_{share_growth:.0%}")

    # Q5: Gross margin stable or rising
    margin_ok = _gross_margin_stable_or_rising(t)
    if margin_ok is None:
        reasons.append("data:margin_unknown")
    elif not margin_ok:
        reasons.append("Q5:margin_eroding")

    return (len(reasons) == 0, reasons)

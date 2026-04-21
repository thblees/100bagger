"""
Fetch per-ticker fundamentals via yfinance 1.x.

Returns a dict with the fields required by filters.py and scoring.py,
or None if essential data is missing.
"""
import yfinance as yf
import pandas as pd
from typing import Optional


def _safe_get(info: dict, *keys, default=None):
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return default


def fetch_fundamentals(ticker: str, exchange: str) -> Optional[dict]:
    """
    Pull fundamentals for a single ticker. Returns None on essential-data gaps.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception:
        return None

    market_cap = _safe_get(info, "marketCap")
    price = _safe_get(info, "currentPrice", "regularMarketPrice", "previousClose")
    ttm_eps = _safe_get(info, "trailingEps")
    sector = _safe_get(info, "sector", default="Unknown")
    name = _safe_get(info, "longName", "shortName", default=ticker)

    if not (market_cap and price):
        return None

    avg_volume_shares = _safe_get(info, "averageVolume10days", "averageVolume", default=0)
    avg_daily_volume_usd = avg_volume_shares * price

    # --- EPS history via earnings_dates ---
    try:
        ed = t.get_earnings_dates(limit=12)
    except Exception:
        return None
    if ed is None or ed.empty or "Reported EPS" not in ed.columns:
        return None

    ed = ed.dropna(subset=["Reported EPS"]).sort_index(ascending=False)
    eps_series = ed["Reported EPS"].astype(float).tolist()
    quarters_available = len(eps_series)
    if quarters_available < 8:
        return None

    def yoy_growth(curr, prev):
        if prev == 0:
            return 0.0 if curr == 0 else (1.0 if curr > 0 else -1.0)
        return (curr - prev) / abs(prev)

    recent_eps = eps_series[:4]
    prior_eps = eps_series[4:8]

    # yoy_eps_growth_rates list: [g_{-3}, g_{-2}, g_{-1}, g_0]  (oldest to newest)
    g_newest_first = [yoy_growth(recent_eps[i], prior_eps[i]) for i in range(4)]
    yoy_eps_growth_rates = list(reversed(g_newest_first))

    mrq_eps = recent_eps[0]
    ttm_eps_calc = sum(recent_eps)
    effective_ttm_eps = ttm_eps if ttm_eps is not None else ttm_eps_calc
    eps_2y_ago = prior_eps[3]  # Q-7

    # --- Revenue yoy growth (1 data point) from quarterly_income_stmt ---
    try:
        q_income = t.quarterly_income_stmt
    except Exception:
        q_income = None

    avg_yoy_revenue_growth = 0.0
    if q_income is not None and not q_income.empty:
        rev_row = None
        for name_candidate in ("Total Revenue", "Operating Revenue"):
            if name_candidate in q_income.index:
                rev_row = q_income.loc[name_candidate]
                break
        if rev_row is not None:
            rev_cols = rev_row.index.sort_values(ascending=False).tolist()
            if len(rev_cols) >= 5:
                q0 = rev_row[rev_cols[0]]
                q_minus_4 = rev_row[rev_cols[4]]
                if not pd.isna(q0) and not pd.isna(q_minus_4):
                    avg_yoy_revenue_growth = yoy_growth(float(q0), float(q_minus_4))

    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "exchange": exchange,
        "market_cap_usd": float(market_cap),
        "price": float(price),
        "ttm_eps": float(effective_ttm_eps),
        "mrq_eps": float(mrq_eps),
        "avg_daily_volume_usd": float(avg_daily_volume_usd),
        "quarters_available": quarters_available,
        "yoy_eps_growth_rates": yoy_eps_growth_rates,
        "avg_yoy_revenue_growth": float(avg_yoy_revenue_growth),
        "current_eps": float(mrq_eps),
        "eps_2y_ago": float(eps_2y_ago),
    }

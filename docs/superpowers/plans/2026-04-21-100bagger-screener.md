# 100-Bagger Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a monthly-refresh screener for US stocks under 500 Mio. USD market cap that scores candidates against Tony's 100-bagger patterns and displays the top 50 in a static HTML dashboard.

**Architecture:** Python pipeline (`pipeline/`) fetches fundamentals via `yfinance`, applies hard filters, scores remaining titles across 5 criteria, writes result to `dashboard/data.json`. Static HTML dashboard (`dashboard/index.html`) loads the JSON and renders a sortable/filterable top-50 table.

**Tech Stack:**
- Python 3.11+, `yfinance`, `pandas`, `requests`, `pytest`
- HTML + Vanilla JS + Tailwind via CDN (no build step)

**Spec reference:** `docs/superpowers/specs/2026-04-21-100bagger-screener-design.md`

---

## File Structure

**Pipeline (Python):**
- `pipeline/universe.py` — fetches the list of US-listed tickers from NASDAQ Trader FTP and returns candidates passing a rough market-cap pre-filter.
- `pipeline/fetch.py` — fetches per-ticker fundamentals via `yfinance` (EPS history, revenue, market cap, volume, sector, price).
- `pipeline/filters.py` — applies the 5 hard filters; returns pass/fail plus reason.
- `pipeline/scoring.py` — contains the 5 scoring functions (EPS acceleration, PEG, market cap, revenue, turnaround) plus total-score aggregator.
- `pipeline/output.py` — assembles the final `data.json` structure.
- `pipeline/run_pipeline.py` — orchestration: ties universe → fetch → filter → score → output together.
- `pipeline/tests/test_scoring.py` — unit tests for all 5 scoring functions.
- `pipeline/tests/test_filters.py` — unit tests for hard-filter logic.
- `pipeline/tests/test_integration.py` — smoke test on 10 known tickers.
- `pipeline/tests/conftest.py` — pytest path setup.
- `pipeline/requirements.txt` — pinned dependencies.

**Dashboard (Frontend):**
- `dashboard/index.html` — complete single-file dashboard.
- `dashboard/data.json` — pipeline output (generated, gitignored pattern but committed as example).

**Meta:**
- `.gitignore` — ignores `__pycache__/`, `*.pyc`, `.pytest_cache/`, `venv/`, `pipeline_log.txt`.

---

## Task 0: Initialize Project

**Files:**
- Create: `.gitignore`
- Create: `pipeline/requirements.txt`
- Create: `pipeline/tests/conftest.py`
- Create: `pipeline/tests/__init__.py`
- Create: `pipeline/__init__.py`

- [ ] **Step 1: Initialize git and create folder skeleton**

Run from the project root (the directory containing `100-baggers.md`):

```bash
git init
mkdir -p pipeline/tests dashboard
touch pipeline/__init__.py pipeline/tests/__init__.py
```

Expected: `.git/` directory created, folders exist.

- [ ] **Step 2: Create `.gitignore`**

Write to `.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
venv/
.venv/
pipeline_log.txt
*.egg-info/
.DS_Store
```

- [ ] **Step 3: Create `pipeline/requirements.txt`**

Write to `pipeline/requirements.txt`:

```
yfinance==1.3.0
pandas==2.3.3
requests==2.32.3
pytest==8.3.2
```

(Pinned to versions compatible with Python 3.14. Earlier versions have no pre-built wheels for 3.14.)

- [ ] **Step 4: Create `pipeline/tests/conftest.py`**

Write to `pipeline/tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

This lets `pytest` import modules from `pipeline/` as top-level.

- [ ] **Step 5: Install dependencies and verify pytest works**

Run:

```bash
python -m venv venv
source venv/Scripts/activate  # Windows bash
pip install -r pipeline/requirements.txt
pytest pipeline/tests/ -v
```

Expected: pytest runs, reports `no tests ran` (fine — no tests yet).

- [ ] **Step 6: Commit**

```bash
git add .gitignore pipeline/ dashboard/
git commit -m "chore: initialize project structure"
```

---

## Task 1: Scoring — EPS Acceleration

**Files:**
- Create: `pipeline/scoring.py`
- Create: `pipeline/tests/test_scoring.py`

- [ ] **Step 1: Write failing test for perfect ladder case**

Write to `pipeline/tests/test_scoring.py`:

```python
from scoring import eps_acceleration_score


def test_perfect_ladder_scores_35():
    # g_{-3}=0.05, g_{-2}=0.15, g_{-1}=0.30, g_0=0.50 — strictly increasing
    assert eps_acceleration_score([0.05, 0.15, 0.30, 0.50]) == 35
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scoring'` or `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Write to `pipeline/scoring.py`:

```python
from typing import List


def eps_acceleration_score(growth_rates: List[float]) -> int:
    """
    Score based on the pattern of yoy-EPS growth rates over the last 4 quarters.

    Input: growth_rates = [g_{-3}, g_{-2}, g_{-1}, g_0]
           as decimals (0.25 = 25% yoy growth).

    Returns an integer score 0..35 per the spec rules.
    """
    if len(growth_rates) != 4:
        raise ValueError("need exactly 4 growth rates")

    g = growth_rates
    steps_up = sum(1 for i in range(1, 4) if g[i] > g[i - 1])

    # Rules evaluated top-down, first match wins
    if steps_up == 3:
        return 35
    if steps_up == 2 and g[3] > g[0]:
        return 25
    if steps_up == 2:
        return 18
    if steps_up == 1 and max(g) in (g[2], g[3]):
        return 10
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: PASS.

- [ ] **Step 5: Add edge-case tests**

Append to `pipeline/tests/test_scoring.py`:

```python
def test_two_steps_up_with_trend_scores_25():
    # g_{-3}=0.10, g_{-2}=0.25, g_{-1}=0.20, g_0=0.40
    # steps: 0.10->0.25 up, 0.25->0.20 down, 0.20->0.40 up => 2 up, g_0 > g_{-3}
    assert eps_acceleration_score([0.10, 0.25, 0.20, 0.40]) == 25


def test_two_steps_up_without_trend_scores_18():
    # g_{-3}=0.40, g_{-2}=0.50, g_{-1}=0.20, g_0=0.35
    # steps: up, down, up => 2 up, g_0 (0.35) < g_{-3} (0.40)
    assert eps_acceleration_score([0.40, 0.50, 0.20, 0.35]) == 18


def test_one_step_up_in_recent_half_scores_10():
    # g_{-3}=0.30, g_{-2}=0.25, g_{-1}=0.15, g_0=0.40
    # steps: down, down, up => 1 up, max is g_0 => 10 points
    assert eps_acceleration_score([0.30, 0.25, 0.15, 0.40]) == 10


def test_declining_scores_0():
    # All down
    assert eps_acceleration_score([0.40, 0.30, 0.20, 0.10]) == 0


def test_flat_scores_0():
    # No steps up (strict inequality)
    assert eps_acceleration_score([0.20, 0.20, 0.20, 0.20]) == 0


def test_wrong_length_raises():
    import pytest
    with pytest.raises(ValueError):
        eps_acceleration_score([0.1, 0.2])
```

- [ ] **Step 6: Run all tests to verify they pass**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: 7 PASS.

- [ ] **Step 7: Commit**

```bash
git add pipeline/scoring.py pipeline/tests/test_scoring.py
git commit -m "feat(scoring): add eps acceleration score"
```

---

## Task 2: Scoring — PEG Ratio

**Files:**
- Modify: `pipeline/scoring.py`
- Modify: `pipeline/tests/test_scoring.py`

- [ ] **Step 1: Write failing tests for PEG scoring**

Append to `pipeline/tests/test_scoring.py`:

```python
from scoring import peg_score


def test_peg_low_scores_25():
    # price=10, ttm_eps=1 (PE=10), g_0=0.50 (50%) => PEG=10/50=0.2
    assert peg_score(price=10.0, ttm_eps=1.0, mrq_eps=0.30, g_0=0.50) == 25


def test_peg_mid_scores_15():
    # price=20, ttm_eps=1, PE=20, g_0=0.30 => PEG=20/30=0.67
    assert peg_score(price=20.0, ttm_eps=1.0, mrq_eps=0.30, g_0=0.30) == 15


def test_peg_high_scores_5():
    # price=40, ttm_eps=1, PE=40, g_0=0.35 => PEG=40/35=1.14
    assert peg_score(price=40.0, ttm_eps=1.0, mrq_eps=0.30, g_0=0.35) == 5


def test_peg_unattractive_scores_0():
    # price=80, ttm_eps=1, PE=80, g_0=0.20 => PEG=80/20=4.0
    assert peg_score(price=80.0, ttm_eps=1.0, mrq_eps=0.30, g_0=0.20) == 0


def test_peg_uses_mrq_annualized_when_ttm_negative():
    # ttm_eps=-0.20 (turnaround), mrq_eps=0.25 => annualized=1.00
    # price=20, effective_PE=20, g_0=0.60 => PEG=20/60=0.33 => 25 pts
    assert peg_score(price=20.0, ttm_eps=-0.20, mrq_eps=0.25, g_0=0.60) == 25


def test_peg_growth_zero_or_negative_scores_0():
    assert peg_score(price=20.0, ttm_eps=1.0, mrq_eps=0.30, g_0=0.0) == 0
    assert peg_score(price=20.0, ttm_eps=1.0, mrq_eps=0.30, g_0=-0.10) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pipeline/tests/test_scoring.py::test_peg_low_scores_25 -v`
Expected: FAIL with `ImportError: cannot import name 'peg_score'`.

- [ ] **Step 3: Implement `peg_score`**

Append to `pipeline/scoring.py`:

```python
def peg_score(price: float, ttm_eps: float, mrq_eps: float, g_0: float) -> int:
    """
    Score based on PEG ratio.

    Uses TTM EPS if positive; falls back to MRQ*4 as annualized proxy when
    TTM is non-positive (turnaround case). MRQ EPS is guaranteed > 0 by the
    hard filter.

    Returns 0..25 per spec thresholds.
    """
    if g_0 <= 0:
        return 0

    effective_eps = ttm_eps if ttm_eps > 0 else mrq_eps * 4
    if effective_eps <= 0:
        return 0

    effective_pe = price / effective_eps
    peg = effective_pe / (g_0 * 100)

    if peg < 0:
        return 0
    if peg < 0.5:
        return 25
    if peg < 1.0:
        return 15
    if peg < 1.5:
        return 5
    return 0
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: all tests PASS (7 + 6 = 13).

- [ ] **Step 5: Commit**

```bash
git add pipeline/scoring.py pipeline/tests/test_scoring.py
git commit -m "feat(scoring): add PEG score with TTM-negative fallback"
```

---

## Task 3: Scoring — Market Cap, Revenue, Turnaround

**Files:**
- Modify: `pipeline/scoring.py`
- Modify: `pipeline/tests/test_scoring.py`

- [ ] **Step 1: Write failing tests for all three functions**

Append to `pipeline/tests/test_scoring.py`:

```python
from scoring import market_cap_score, revenue_score, turnaround_score


def test_market_cap_below_100m():
    assert market_cap_score(80_000_000) == 15


def test_market_cap_below_250m():
    assert market_cap_score(200_000_000) == 10


def test_market_cap_below_500m():
    assert market_cap_score(400_000_000) == 5


def test_market_cap_above_500m():
    assert market_cap_score(600_000_000) == 0


def test_revenue_high_growth():
    assert revenue_score(0.35) == 15


def test_revenue_mid_growth():
    assert revenue_score(0.20) == 8


def test_revenue_low_growth():
    assert revenue_score(0.08) == 3


def test_revenue_no_growth():
    assert revenue_score(0.02) == 0


def test_turnaround_active():
    # Old EPS was negative, current is positive, accel score >= 20
    assert turnaround_score(eps_2y_ago=-0.10, current_eps=0.05, accel_score=25) == 10


def test_turnaround_requires_old_loss():
    assert turnaround_score(eps_2y_ago=0.05, current_eps=0.10, accel_score=25) == 0


def test_turnaround_requires_current_profit():
    assert turnaround_score(eps_2y_ago=-0.10, current_eps=-0.02, accel_score=25) == 0


def test_turnaround_requires_accel_score():
    assert turnaround_score(eps_2y_ago=-0.10, current_eps=0.05, accel_score=18) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: 12 FAIL with import errors.

- [ ] **Step 3: Implement the three functions**

Append to `pipeline/scoring.py`:

```python
def market_cap_score(market_cap_usd: float) -> int:
    """Smaller is better (more room for 100x). Returns 0..15."""
    if market_cap_usd < 100_000_000:
        return 15
    if market_cap_usd < 250_000_000:
        return 10
    if market_cap_usd < 500_000_000:
        return 5
    return 0


def revenue_score(avg_yoy_revenue_growth: float) -> int:
    """Supports EPS-growth quality. Returns 0..15."""
    if avg_yoy_revenue_growth > 0.30:
        return 15
    if avg_yoy_revenue_growth > 0.15:
        return 8
    if avg_yoy_revenue_growth > 0.05:
        return 3
    return 0


def turnaround_score(eps_2y_ago: float, current_eps: float, accel_score: int) -> int:
    """Bonus for classic turnaround pattern. Returns 0 or 10."""
    if eps_2y_ago <= 0 and current_eps > 0 and accel_score >= 20:
        return 10
    return 0
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: all 25 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline/scoring.py pipeline/tests/test_scoring.py
git commit -m "feat(scoring): add market cap, revenue, turnaround scores"
```

---

## Task 4: Scoring — Total Aggregator

**Files:**
- Modify: `pipeline/scoring.py`
- Modify: `pipeline/tests/test_scoring.py`

- [ ] **Step 1: Write failing test**

Append to `pipeline/tests/test_scoring.py`:

```python
from scoring import score_company


def test_score_company_aggregates_all():
    fundamentals = {
        "yoy_eps_growth_rates": [0.05, 0.15, 0.30, 0.50],  # perfect ladder => 35
        "price": 10.0,
        "ttm_eps": 1.0,
        "mrq_eps": 0.30,  # g_0 = 0.50 => PEG=0.2 => 25
        "market_cap_usd": 80_000_000,  # => 15
        "avg_yoy_revenue_growth": 0.35,  # => 15
        "eps_2y_ago": -0.10,
        "current_eps": 0.30,  # turnaround active => 10
    }
    result = score_company(fundamentals)
    assert result["total_score"] == 100
    assert result["eps_accel_score"] == 35
    assert result["peg_score"] == 25
    assert result["mcap_score"] == 15
    assert result["revenue_score"] == 15
    assert result["turnaround_score"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pipeline/tests/test_scoring.py::test_score_company_aggregates_all -v`
Expected: FAIL with `ImportError: cannot import name 'score_company'`.

- [ ] **Step 3: Implement `score_company`**

Append to `pipeline/scoring.py`:

```python
def score_company(f: dict) -> dict:
    """
    Compute all 5 score components plus total for one company.

    Input `f` must contain:
      yoy_eps_growth_rates, price, ttm_eps, mrq_eps, market_cap_usd,
      avg_yoy_revenue_growth, eps_2y_ago, current_eps

    Returns a dict with the 5 component scores and total_score.
    """
    accel = eps_acceleration_score(f["yoy_eps_growth_rates"])
    peg = peg_score(
        price=f["price"],
        ttm_eps=f["ttm_eps"],
        mrq_eps=f["mrq_eps"],
        g_0=f["yoy_eps_growth_rates"][3],
    )
    mcap = market_cap_score(f["market_cap_usd"])
    rev = revenue_score(f["avg_yoy_revenue_growth"])
    turn = turnaround_score(
        eps_2y_ago=f["eps_2y_ago"],
        current_eps=f["current_eps"],
        accel_score=accel,
    )
    return {
        "eps_accel_score": accel,
        "peg_score": peg,
        "mcap_score": mcap,
        "revenue_score": rev,
        "turnaround_score": turn,
        "total_score": accel + peg + mcap + rev + turn,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest pipeline/tests/test_scoring.py -v`
Expected: all 26 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline/scoring.py pipeline/tests/test_scoring.py
git commit -m "feat(scoring): add score_company aggregator"
```

---

## Task 5: Hard Filters

**Files:**
- Create: `pipeline/filters.py`
- Create: `pipeline/tests/test_filters.py`

- [ ] **Step 1: Write failing tests**

Write to `pipeline/tests/test_filters.py`:

```python
from filters import passes_hard_filter


BASE = {
    "market_cap_usd": 300_000_000,
    "mrq_eps": 0.15,
    "avg_daily_volume_usd": 250_000,
    "quarters_available": 10,
    "exchange": "NASDAQ",
}


def test_valid_passes():
    ok, reason = passes_hard_filter(BASE)
    assert ok is True
    assert reason == ""


def test_market_cap_too_large_fails():
    bad = {**BASE, "market_cap_usd": 700_000_000}
    ok, reason = passes_hard_filter(bad)
    assert ok is False
    assert "market_cap" in reason


def test_mrq_eps_not_positive_fails():
    bad = {**BASE, "mrq_eps": -0.05}
    ok, reason = passes_hard_filter(bad)
    assert ok is False
    assert "mrq_eps" in reason


def test_low_volume_fails():
    bad = {**BASE, "avg_daily_volume_usd": 50_000}
    ok, reason = passes_hard_filter(bad)
    assert ok is False
    assert "volume" in reason


def test_insufficient_history_fails():
    bad = {**BASE, "quarters_available": 5}
    ok, reason = passes_hard_filter(bad)
    assert ok is False
    assert "history" in reason


def test_wrong_exchange_fails():
    bad = {**BASE, "exchange": "OTC"}
    ok, reason = passes_hard_filter(bad)
    assert ok is False
    assert "exchange" in reason


def test_nyse_and_amex_pass():
    for ex in ("NYSE", "NYSE AMERICAN", "AMEX"):
        ok, _ = passes_hard_filter({**BASE, "exchange": ex})
        assert ok is True, f"{ex} should pass"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pipeline/tests/test_filters.py -v`
Expected: all FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `passes_hard_filter`**

Write to `pipeline/filters.py`:

```python
from typing import Tuple

ALLOWED_EXCHANGES = {"NASDAQ", "NYSE", "NYSE AMERICAN", "AMEX"}

MAX_MARKET_CAP_USD = 500_000_000
MIN_DAILY_VOLUME_USD = 100_000
MIN_QUARTERS_HISTORY = 8


def passes_hard_filter(f: dict) -> Tuple[bool, str]:
    """
    Check if a company's fundamentals pass all 5 hard filters.

    Returns (True, "") on pass, or (False, "<reason>") on fail.
    """
    if f.get("market_cap_usd", 0) >= MAX_MARKET_CAP_USD:
        return False, f"market_cap too large: {f.get('market_cap_usd')}"
    if f.get("mrq_eps", 0) <= 0:
        return False, f"mrq_eps not positive: {f.get('mrq_eps')}"
    if f.get("avg_daily_volume_usd", 0) < MIN_DAILY_VOLUME_USD:
        return False, f"volume too low: {f.get('avg_daily_volume_usd')}"
    if f.get("quarters_available", 0) < MIN_QUARTERS_HISTORY:
        return False, f"insufficient history: {f.get('quarters_available')} quarters"
    if f.get("exchange", "").upper() not in ALLOWED_EXCHANGES:
        return False, f"unsupported exchange: {f.get('exchange')}"
    return True, ""
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `pytest pipeline/tests/test_filters.py -v`
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline/filters.py pipeline/tests/test_filters.py
git commit -m "feat(filters): add hard filter logic"
```

---

## Task 6: Universe Fetcher

**Files:**
- Create: `pipeline/universe.py`
- Modify: `pipeline/tests/` — manual smoke test, no automated test (hits external FTP)

NASDAQ Trader publishes two daily-refreshed ticker lists: `nasdaqlisted.txt` (NASDAQ-listed) and `otherlisted.txt` (NYSE, AMEX, NYSE American). These are pipe-delimited text files served over HTTP at `https://www.nasdaqtrader.com/dynamic/SymDir/`.

- [ ] **Step 1: Implement `universe.py`**

Write to `pipeline/universe.py`:

```python
"""
Fetch the list of US-listed equity tickers from NASDAQ Trader.

Returns a list of dicts: [{"ticker": "AAPL", "name": "...", "exchange": "NASDAQ"}, ...]

NASDAQ Trader publishes the official ticker directory at:
  https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt  (pipe-delimited)
  https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt   (pipe-delimited)

We filter out ETFs, test issues, and tickers with special characters
(warrants, preferred shares, units).
"""
import io
import requests
import pandas as pd

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def _fetch_csv(url: str) -> pd.DataFrame:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    # Last line is a "File Creation Time" footer — drop it
    content = "\n".join(resp.text.splitlines()[:-1])
    return pd.read_csv(io.StringIO(content), sep="|")


def fetch_us_tickers() -> list[dict]:
    """Returns a list of equity tickers across NASDAQ, NYSE, AMEX."""
    results = []

    df_nasdaq = _fetch_csv(NASDAQ_URL)
    # Columns: Symbol, Security Name, Market Category, Test Issue, Financial Status,
    # Round Lot Size, ETF, NextShares
    df_nasdaq = df_nasdaq[
        (df_nasdaq["Test Issue"] == "N")
        & (df_nasdaq["ETF"] == "N")
        & (~df_nasdaq["Symbol"].astype(str).str.contains(r"[\.\$\+\-]", regex=True))
    ]
    for _, row in df_nasdaq.iterrows():
        results.append(
            {
                "ticker": str(row["Symbol"]).strip(),
                "name": str(row["Security Name"]).strip(),
                "exchange": "NASDAQ",
            }
        )

    df_other = _fetch_csv(OTHER_URL)
    # Columns: ACT Symbol, Security Name, Exchange, CQS Symbol, ETF, Round Lot Size,
    # Test Issue, NASDAQ Symbol
    df_other = df_other[
        (df_other["Test Issue"] == "N")
        & (df_other["ETF"] == "N")
        & (~df_other["ACT Symbol"].astype(str).str.contains(r"[\.\$\+\-]", regex=True))
    ]
    exchange_map = {
        "N": "NYSE",
        "A": "NYSE AMERICAN",
        "P": "NYSE ARCA",
        "Z": "BATS",
    }
    for _, row in df_other.iterrows():
        ex = exchange_map.get(str(row["Exchange"]).strip(), str(row["Exchange"]))
        if ex in ("NYSE ARCA", "BATS"):
            continue  # ARCA = ETF venue; BATS = rare
        results.append(
            {
                "ticker": str(row["ACT Symbol"]).strip(),
                "name": str(row["Security Name"]).strip(),
                "exchange": ex,
            }
        )

    return results


if __name__ == "__main__":
    tickers = fetch_us_tickers()
    print(f"Fetched {len(tickers)} US-listed equities.")
    print("Sample:", tickers[:5])
```

- [ ] **Step 2: Smoke test the fetcher**

Run:

```bash
python pipeline/universe.py
```

Expected output: prints roughly `Fetched 6000-8000 US-listed equities.` plus a 5-ticker sample. If HTTP fails, investigate `nasdaqtrader.com` reachability before proceeding.

- [ ] **Step 3: Commit**

```bash
git add pipeline/universe.py
git commit -m "feat(universe): fetch US tickers from NASDAQ Trader"
```

---

## Task 7: Company-Fundamentals Fetcher

**Files:**
- Create: `pipeline/fetch.py`

**Data sources used per field** (probed empirically on yfinance 1.3.0):

| Field | Source | Notes |
|-------|--------|-------|
| market_cap, price, ttm_eps, sector, name, exchange | `Ticker.info` | Standard metadata |
| avg_daily_volume_usd | `info["averageVolume10days"] * price` | 10-day avg |
| quarterly EPS history (≥8 quarters) | `Ticker.get_earnings_dates(limit=12)` column `"Reported EPS"` | yfinance 1.x returns up to ~50 quarters. Must skip future rows where `"Reported EPS"` is NaN. |
| revenue (5 quarters) | `Ticker.quarterly_income_stmt` | Only 5 quarters available → 1 yoy-revenue comparison (Q0 vs Q-4) |

**Scope change vs original spec:** `avg_yoy_revenue_growth` was defined as average over the last 4 quarters in the spec. Because quarterly revenue history is limited to 5 quarters, we use a single yoy comparison (Q0 vs Q-4). Scoring semantics unchanged — the field name stays but represents one yoy rate, not a 4-quarter average.

- [ ] **Step 1: Implement `fetch_fundamentals`**

Write to `pipeline/fetch.py`:

```python
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

    # --- EPS history via earnings_dates (gives 20+ quarters on most tickers) ---
    try:
        ed = t.get_earnings_dates(limit=12)
    except Exception:
        return None
    if ed is None or ed.empty or "Reported EPS" not in ed.columns:
        return None

    # Drop future/unreported rows (NaN in Reported EPS), sort newest-first
    ed = ed.dropna(subset=["Reported EPS"]).sort_index(ascending=False)
    eps_series = ed["Reported EPS"].astype(float).tolist()
    quarters_available = len(eps_series)
    if quarters_available < 8:
        return None

    # yoy_eps_growth_rates: compare Q_i to Q_{i-4}
    def yoy_growth(curr, prev):
        if prev == 0:
            return 0.0 if curr == 0 else (1.0 if curr > 0 else -1.0)
        return (curr - prev) / abs(prev)

    # Indices 0..3 = recent 4 quarters (newest first), 4..7 = year-ago same quarters
    recent_eps = eps_series[:4]
    prior_eps = eps_series[4:8]

    # yoy_eps_growth_rates list: [g_{-3}, g_{-2}, g_{-1}, g_0]  (oldest to newest)
    g_newest_first = [yoy_growth(recent_eps[i], prior_eps[i]) for i in range(4)]
    yoy_eps_growth_rates = list(reversed(g_newest_first))

    mrq_eps = recent_eps[0]
    ttm_eps_calc = sum(recent_eps)
    effective_ttm_eps = ttm_eps if ttm_eps is not None else ttm_eps_calc
    eps_2y_ago = prior_eps[3]  # Q-7

    # --- Revenue yoy growth from quarterly_income_stmt (5 quarters) ---
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
```

- [ ] **Step 2: Smoke test with a known ticker**

Run:

```bash
python -c "from pipeline.fetch import fetch_fundamentals; import json; print(json.dumps(fetch_fundamentals('MED', 'NYSE'), indent=2, default=str))"
```

Expected: A JSON blob with all expected fields populated. If any key field is missing, investigate the `yfinance` field name — it may have changed.

- [ ] **Step 3: Commit**

```bash
git add pipeline/fetch.py
git commit -m "feat(fetch): add yfinance-based fundamentals fetcher"
```

---

## Task 8: Output Writer

**Files:**
- Create: `pipeline/output.py`
- Create: `pipeline/tests/test_output.py`

- [ ] **Step 1: Write failing test**

Write to `pipeline/tests/test_output.py`:

```python
import json
from pathlib import Path

from output import assemble_output, write_output


def test_assemble_output_sorts_and_caps():
    scored = [
        {"ticker": "AAA", "total_score": 50},
        {"ticker": "BBB", "total_score": 80},
        {"ticker": "CCC", "total_score": 65},
    ]
    result = assemble_output(
        scored_companies=scored,
        universe_size=1000,
        passed_hard_filter=3,
        generated_at="2026-04-21",
        top_n=2,
    )
    assert result["generated_at"] == "2026-04-21"
    assert result["universe_size"] == 1000
    assert result["passed_hard_filter"] == 3
    assert len(result["top_results"]) == 2
    assert result["top_results"][0]["ticker"] == "BBB"
    assert result["top_results"][1]["ticker"] == "CCC"


def test_write_output_creates_valid_json(tmp_path: Path):
    payload = {"generated_at": "2026-04-21", "top_results": []}
    target = tmp_path / "data.json"
    write_output(payload, target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pipeline/tests/test_output.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `output.py`**

Write to `pipeline/output.py`:

```python
import json
from pathlib import Path


def assemble_output(
    scored_companies: list[dict],
    universe_size: int,
    passed_hard_filter: int,
    generated_at: str,
    top_n: int = 50,
) -> dict:
    """Sort scored companies by total_score desc, keep top N, build payload."""
    sorted_companies = sorted(
        scored_companies, key=lambda c: c["total_score"], reverse=True
    )
    top = sorted_companies[:top_n]
    return {
        "generated_at": generated_at,
        "universe_size": universe_size,
        "passed_hard_filter": passed_hard_filter,
        "top_results": top,
    }


def write_output(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pipeline/tests/test_output.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline/output.py pipeline/tests/test_output.py
git commit -m "feat(output): add JSON assembly and writer"
```

---

## Task 9: Pipeline Orchestration

**Files:**
- Create: `pipeline/run_pipeline.py`

Orchestration script: fetch universe → per-ticker fetch + filter + score → assemble → write. Logs progress and errors, tolerates single-ticker failures.

- [ ] **Step 1: Implement `run_pipeline.py`**

Write to `pipeline/run_pipeline.py`:

```python
"""
Main orchestration: run the 100-bagger screener end-to-end.

Usage:
    python pipeline/run_pipeline.py

Output:
    dashboard/data.json
    pipeline/pipeline_log.txt
"""
import sys
import time
import traceback
from datetime import date
from pathlib import Path

# Allow running as `python pipeline/run_pipeline.py`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from universe import fetch_us_tickers
from fetch import fetch_fundamentals
from filters import passes_hard_filter
from scoring import score_company
from output import assemble_output, write_output


LOG_PATH = ROOT / "pipeline" / "pipeline_log.txt"
OUTPUT_PATH = ROOT / "dashboard" / "data.json"


def log(msg: str, log_file) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line)
    log_file.write(line + "\n")
    log_file.flush()


def main():
    with LOG_PATH.open("w", encoding="utf-8") as lf:
        log("Fetching US ticker universe...", lf)
        tickers = fetch_us_tickers()
        log(f"Universe size: {len(tickers)} tickers", lf)

        scored = []
        n_skipped = 0
        n_filtered = 0
        n_passed = 0

        for idx, t in enumerate(tickers):
            if idx % 100 == 0 and idx > 0:
                log(
                    f"Progress: {idx}/{len(tickers)} — passed: {n_passed}, "
                    f"filtered: {n_filtered}, skipped: {n_skipped}",
                    lf,
                )

            try:
                f = fetch_fundamentals(t["ticker"], t["exchange"])
            except Exception as e:
                n_skipped += 1
                log(f"skipped {t['ticker']}: fetch error {e.__class__.__name__}", lf)
                continue

            if f is None:
                n_skipped += 1
                continue

            ok, reason = passes_hard_filter(f)
            if not ok:
                n_filtered += 1
                continue

            try:
                scores = score_company(f)
            except Exception as e:
                n_skipped += 1
                log(f"skipped {t['ticker']}: scoring error {e}", lf)
                continue

            scored.append(
                {
                    "ticker": f["ticker"],
                    "name": f["name"],
                    "sector": f["sector"],
                    "exchange": f["exchange"],
                    "market_cap_usd": f["market_cap_usd"],
                    "price": f["price"],
                    "ttm_eps": f["ttm_eps"],
                    "mrq_eps": f["mrq_eps"],
                    "avg_daily_volume_usd": f["avg_daily_volume_usd"],
                    "ttm_pe": f["price"] / f["ttm_eps"] if f["ttm_eps"] > 0 else None,
                    "yoy_eps_growth_rates": f["yoy_eps_growth_rates"],
                    "avg_yoy_revenue_growth": f["avg_yoy_revenue_growth"],
                    **scores,
                }
            )
            n_passed += 1

        log(
            f"Done. passed={n_passed}, filtered={n_filtered}, skipped={n_skipped}",
            lf,
        )

        payload = assemble_output(
            scored_companies=scored,
            universe_size=len(tickers),
            passed_hard_filter=n_passed,
            generated_at=str(date.today()),
            top_n=50,
        )
        write_output(payload, OUTPUT_PATH)
        log(f"Wrote {OUTPUT_PATH} with {len(payload['top_results'])} top results.", lf)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
```

- [ ] **Step 2: Run a small-scope smoke test**

We don't want to wait 30-60 min for a full run. Instead, run a short smoke test that limits the universe to 10 known tickers.

Create a temporary test file:

Write to `pipeline/smoke_test.py`:

```python
"""Short smoke test: run the pipeline on 10 hand-picked tickers."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch import fetch_fundamentals
from filters import passes_hard_filter
from scoring import score_company
from output import assemble_output, write_output


TICKERS = [
    ("MED", "NYSE"),
    ("GMCR", "NASDAQ"),
    ("TASR", "NASDAQ"),
    ("BYI", "NYSE"),
    ("MIDD", "NASDAQ"),
    ("ASFI", "NASDAQ"),
    ("NTRI", "NASDAQ"),
    ("HANS", "NASDAQ"),
    ("DELL", "NYSE"),
    ("ERTS", "NASDAQ"),
]


def main():
    scored = []
    for ticker, exchange in TICKERS:
        f = fetch_fundamentals(ticker, exchange)
        if f is None:
            print(f"{ticker}: fetch returned None (likely delisted or data missing)")
            continue
        ok, reason = passes_hard_filter(f)
        print(f"{ticker}: pass={ok} reason={reason or 'ok'}")
        if not ok:
            continue
        scores = score_company(f)
        scored.append({"ticker": ticker, **scores})

    payload = assemble_output(
        scored_companies=scored,
        universe_size=len(TICKERS),
        passed_hard_filter=len(scored),
        generated_at=str(date.today()),
        top_n=50,
    )
    out = Path(__file__).resolve().parents[1] / "dashboard" / "data.json"
    write_output(payload, out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

Run:

```bash
python pipeline/smoke_test.py
```

Expected: For each ticker, either "pass=True" with printed scores, or a clear skip reason. `dashboard/data.json` is created. Some of these tickers are delisted (HANS, ERTS, BYI, ASFI were renamed/acquired); they may return None. That's OK — MED, GMCR, NTRI, MIDD, DELL should still return data (DELL went private in 2013; a modern replacement for smoke testing can be used if needed).

If many tickers fail, investigate: did the `yfinance` field names change? Is `quarterly_income_stmt` returning something different?

- [ ] **Step 3: Delete the smoke test file (not needed in repo)**

```bash
rm pipeline/smoke_test.py
```

- [ ] **Step 4: Commit**

```bash
git add pipeline/run_pipeline.py
git commit -m "feat(pipeline): add main orchestration"
```

---

## Task 10: Integration Test

**Files:**
- Create: `pipeline/tests/test_integration.py`

This test does NOT hit the network. It tests the pipeline's internal wiring using mocked data.

- [ ] **Step 1: Write failing integration test**

Write to `pipeline/tests/test_integration.py`:

```python
from unittest.mock import patch

from filters import passes_hard_filter
from scoring import score_company
from output import assemble_output


def make_fixture(ticker="TEST", market_cap=200_000_000, mrq_eps=0.20):
    return {
        "ticker": ticker,
        "name": f"{ticker} Corp",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "market_cap_usd": market_cap,
        "price": 12.0,
        "ttm_eps": 0.80,
        "mrq_eps": mrq_eps,
        "avg_daily_volume_usd": 500_000,
        "quarters_available": 12,
        "yoy_eps_growth_rates": [0.10, 0.20, 0.30, 0.50],
        "avg_yoy_revenue_growth": 0.25,
        "current_eps": mrq_eps,
        "eps_2y_ago": -0.05,
    }


def test_full_chain_one_company():
    f = make_fixture()
    ok, reason = passes_hard_filter(f)
    assert ok, reason

    scores = score_company(f)
    assert scores["total_score"] > 0
    assert 0 <= scores["eps_accel_score"] <= 35
    assert 0 <= scores["peg_score"] <= 25
    assert 0 <= scores["mcap_score"] <= 15
    assert 0 <= scores["revenue_score"] <= 15
    assert 0 <= scores["turnaround_score"] <= 10


def test_assemble_handles_empty_list():
    payload = assemble_output(
        scored_companies=[],
        universe_size=100,
        passed_hard_filter=0,
        generated_at="2026-04-21",
    )
    assert payload["top_results"] == []
    assert payload["universe_size"] == 100


def test_assemble_sorts_multiple():
    companies = [
        {"ticker": "A", "total_score": 30, "name": "A"},
        {"ticker": "B", "total_score": 80, "name": "B"},
        {"ticker": "C", "total_score": 55, "name": "C"},
    ]
    payload = assemble_output(
        scored_companies=companies,
        universe_size=100,
        passed_hard_filter=3,
        generated_at="2026-04-21",
    )
    scores = [c["total_score"] for c in payload["top_results"]]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest pipeline/tests/ -v`
Expected: all ~30 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add pipeline/tests/test_integration.py
git commit -m "test: add pipeline integration tests"
```

---

## Task 11: Dashboard — Skeleton and Table Rendering

**Files:**
- Create: `dashboard/index.html`

Single-file dashboard. Loads `data.json` via `fetch()` on page load.

- [ ] **Step 1: Write `dashboard/index.html` skeleton with table**

Write to `dashboard/index.html`:

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>100-Bagger Screener</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900">
  <div class="max-w-7xl mx-auto p-6">
    <header class="mb-6 flex justify-between items-start">
      <div>
        <h1 class="text-3xl font-bold">100-Bagger Screener</h1>
        <p class="text-sm text-slate-600 mt-1" id="meta">Lade...</p>
      </div>
      <button id="explainer-btn"
        class="bg-slate-800 text-white px-4 py-2 rounded-md text-sm hover:bg-slate-700">
        Wie funktioniert der Screener?
      </button>
    </header>

    <div id="error-banner" class="hidden bg-red-100 border border-red-300 text-red-800 p-4 rounded mb-4"></div>

    <div class="overflow-x-auto bg-white rounded-lg shadow">
      <table class="min-w-full text-sm" id="results-table">
        <thead class="bg-slate-100 text-left text-xs uppercase tracking-wider">
          <tr id="header-row">
            <th class="px-3 py-2 cursor-pointer" data-col="rank">#</th>
            <th class="px-3 py-2 cursor-pointer" data-col="ticker">Ticker</th>
            <th class="px-3 py-2 cursor-pointer" data-col="name">Name</th>
            <th class="px-3 py-2 cursor-pointer" data-col="sector">Sektor</th>
            <th class="px-3 py-2 cursor-pointer text-right" data-col="market_cap_usd">Mkt Cap</th>
            <th class="px-3 py-2 cursor-pointer text-right font-bold" data-col="total_score">Score</th>
            <th class="px-3 py-2 text-right">Accel</th>
            <th class="px-3 py-2 text-right">PEG</th>
            <th class="px-3 py-2 text-right">MCap</th>
            <th class="px-3 py-2 text-right">Rev</th>
            <th class="px-3 py-2 text-right">Turn</th>
            <th class="px-3 py-2 text-right">TTM PE</th>
            <th class="px-3 py-2 text-right">g0</th>
            <th class="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody id="results-body"></tbody>
      </table>
    </div>
  </div>

  <div id="detail-modal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
      <div id="modal-content"></div>
      <button id="close-modal" class="mt-4 bg-slate-800 text-white px-4 py-2 rounded text-sm">Schließen</button>
    </div>
  </div>

  <script>
    const state = { data: null, filteredRows: [], sortCol: "total_score", sortDir: "desc" };

    function formatUSD(n) {
      if (n == null) return "n/a";
      if (n >= 1e9) return (n / 1e9).toFixed(2) + " Mrd";
      if (n >= 1e6) return (n / 1e6).toFixed(1) + " Mio";
      return n.toLocaleString();
    }

    function formatPct(n) {
      if (n == null) return "n/a";
      return (n * 100).toFixed(1) + "%";
    }

    function renderTable(rows) {
      const tbody = document.getElementById("results-body");
      tbody.innerHTML = "";
      rows.forEach((r, idx) => {
        const tr = document.createElement("tr");
        tr.className = "border-t hover:bg-slate-50 cursor-pointer";
        tr.innerHTML = `
          <td class="px-3 py-2 text-slate-500">${idx + 1}</td>
          <td class="px-3 py-2 font-semibold">${r.ticker}</td>
          <td class="px-3 py-2">${r.name}</td>
          <td class="px-3 py-2 text-slate-600">${r.sector}</td>
          <td class="px-3 py-2 text-right">${formatUSD(r.market_cap_usd)}</td>
          <td class="px-3 py-2 text-right font-bold">${r.total_score}</td>
          <td class="px-3 py-2 text-right">${r.eps_accel_score}</td>
          <td class="px-3 py-2 text-right">${r.peg_score}</td>
          <td class="px-3 py-2 text-right">${r.mcap_score}</td>
          <td class="px-3 py-2 text-right">${r.revenue_score}</td>
          <td class="px-3 py-2 text-right">${r.turnaround_score}</td>
          <td class="px-3 py-2 text-right">${r.ttm_pe ? r.ttm_pe.toFixed(1) : "n/a"}</td>
          <td class="px-3 py-2 text-right">${formatPct(r.yoy_eps_growth_rates?.[3])}</td>
          <td class="px-3 py-2"><a href="https://finance.yahoo.com/quote/${r.ticker}" target="_blank" class="text-blue-600 hover:underline">↗</a></td>
        `;
        tr.addEventListener("click", (e) => {
          if (e.target.tagName === "A") return;
          showDetail(r);
        });
        tbody.appendChild(tr);
      });
    }

    function showDetail(r) {
      document.getElementById("modal-content").innerHTML = `
        <h2 class="text-2xl font-bold mb-2">${r.ticker} — ${r.name}</h2>
        <p class="text-slate-600 mb-4">${r.sector} · ${r.exchange}</p>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div><span class="text-slate-500">Market Cap:</span> ${formatUSD(r.market_cap_usd)}</div>
          <div><span class="text-slate-500">Preis:</span> $${r.price?.toFixed(2)}</div>
          <div><span class="text-slate-500">TTM EPS:</span> $${r.ttm_eps?.toFixed(2)}</div>
          <div><span class="text-slate-500">MRQ EPS:</span> $${r.mrq_eps?.toFixed(2)}</div>
          <div><span class="text-slate-500">TTM PE:</span> ${r.ttm_pe ? r.ttm_pe.toFixed(1) : "n/a"}</div>
          <div><span class="text-slate-500">Avg Vol $:</span> ${formatUSD(r.avg_daily_volume_usd)}</div>
        </div>
        <h3 class="font-semibold mt-4 mb-1">yoy-EPS-Wachstum (4 Q, älteste → neueste):</h3>
        <div class="text-sm">${(r.yoy_eps_growth_rates || []).map(formatPct).join("  →  ")}</div>
        <h3 class="font-semibold mt-4 mb-2">Score-Komponenten (${r.total_score}/100):</h3>
        <table class="text-sm w-full">
          <tr><td class="py-1">EPS-Beschleunigung</td><td class="text-right">${r.eps_accel_score}/35</td></tr>
          <tr><td class="py-1">PEG</td><td class="text-right">${r.peg_score}/25</td></tr>
          <tr><td class="py-1">Market Cap klein</td><td class="text-right">${r.mcap_score}/15</td></tr>
          <tr><td class="py-1">Umsatzwachstum (${formatPct(r.avg_yoy_revenue_growth)})</td><td class="text-right">${r.revenue_score}/15</td></tr>
          <tr><td class="py-1">Turnaround-Bonus</td><td class="text-right">${r.turnaround_score}/10</td></tr>
        </table>
      `;
      document.getElementById("detail-modal").classList.remove("hidden");
    }

    document.getElementById("close-modal").addEventListener("click", () => {
      document.getElementById("detail-modal").classList.add("hidden");
    });
    document.getElementById("detail-modal").addEventListener("click", (e) => {
      if (e.target.id === "detail-modal") {
        document.getElementById("detail-modal").classList.add("hidden");
      }
    });

    async function load() {
      try {
        const resp = await fetch("data.json");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        state.data = data;
        document.getElementById("meta").textContent =
          `Stand ${data.generated_at} · ${data.universe_size.toLocaleString()} Titel gescreent · ${data.passed_hard_filter} durch Hard-Filter · Top ${data.top_results.length} angezeigt`;
        state.filteredRows = data.top_results.slice();
        renderTable(state.filteredRows);
      } catch (e) {
        const banner = document.getElementById("error-banner");
        banner.textContent = `Datenfile konnte nicht geladen werden: ${e.message}. Liegt dashboard/data.json vor?`;
        banner.classList.remove("hidden");
      }
    }

    load();
  </script>
</body>
</html>
```

- [ ] **Step 2: Smoke-test the dashboard locally**

Create a minimal test data file:

Write to `dashboard/data.json`:

```json
{
  "generated_at": "2026-04-21",
  "universe_size": 3247,
  "passed_hard_filter": 412,
  "top_results": [
    {
      "ticker": "XYZ",
      "name": "Example Corp",
      "sector": "Technology",
      "exchange": "NASDAQ",
      "market_cap_usd": 187500000,
      "price": 12.50,
      "ttm_eps": 0.42,
      "mrq_eps": 0.14,
      "avg_daily_volume_usd": 1240000,
      "ttm_pe": 29.8,
      "yoy_eps_growth_rates": [0.05, 0.18, 0.34, 0.61],
      "avg_yoy_revenue_growth": 0.27,
      "eps_accel_score": 35,
      "peg_score": 25,
      "mcap_score": 10,
      "revenue_score": 8,
      "turnaround_score": 0,
      "total_score": 78
    },
    {
      "ticker": "ABC",
      "name": "Another Example",
      "sector": "Industrials",
      "exchange": "NYSE",
      "market_cap_usd": 350000000,
      "price": 25.0,
      "ttm_eps": 1.50,
      "mrq_eps": 0.45,
      "avg_daily_volume_usd": 800000,
      "ttm_pe": 16.7,
      "yoy_eps_growth_rates": [0.40, 0.30, 0.25, 0.20],
      "avg_yoy_revenue_growth": 0.12,
      "eps_accel_score": 0,
      "peg_score": 15,
      "mcap_score": 5,
      "revenue_score": 3,
      "turnaround_score": 0,
      "total_score": 23
    }
  ]
}
```

Then serve the dashboard folder:

```bash
cd dashboard && python -m http.server 8080
```

Open `http://localhost:8080` in a browser. Expected: header with meta line, 2-row table, click row → modal with detail.

Stop the server with Ctrl+C.

- [ ] **Step 3: Commit**

```bash
git add dashboard/index.html dashboard/data.json
git commit -m "feat(dashboard): add base HTML + table rendering"
```

---

## Task 12: Dashboard — Sorting and Filtering

**Files:**
- Modify: `dashboard/index.html`

- [ ] **Step 1: Add sorting and filter UI**

Replace the `<div class="overflow-x-auto ...">` block with this extended version (adds a filter bar above the table):

```html
<div class="bg-white rounded-lg shadow p-4 mb-4 grid grid-cols-1 md:grid-cols-4 gap-3">
  <div>
    <label class="block text-xs text-slate-600 mb-1">Suche (Ticker/Name)</label>
    <input type="text" id="filter-search" class="w-full border border-slate-300 rounded px-2 py-1 text-sm" placeholder="z.B. MED" />
  </div>
  <div>
    <label class="block text-xs text-slate-600 mb-1">Sektor</label>
    <select id="filter-sector" class="w-full border border-slate-300 rounded px-2 py-1 text-sm">
      <option value="">Alle</option>
    </select>
  </div>
  <div>
    <label class="block text-xs text-slate-600 mb-1">Min. Score: <span id="score-val">0</span></label>
    <input type="range" id="filter-score" min="0" max="100" value="0" class="w-full" />
  </div>
  <div>
    <label class="block text-xs text-slate-600 mb-1">Max. Market Cap (Mio $): <span id="mcap-val">500</span></label>
    <input type="range" id="filter-mcap" min="0" max="500" value="500" class="w-full" />
  </div>
</div>

<div class="overflow-x-auto bg-white rounded-lg shadow">
  <table class="min-w-full text-sm" id="results-table">
```

(Keep the rest of the `<table>` block identical to Task 11.)

- [ ] **Step 2: Add filtering + sorting JS logic**

Inside the `<script>` block, before `load()` is called, add these new functions and replace the existing renderTable-body with them:

```javascript
function getFilteredRows() {
  if (!state.data) return [];
  const search = document.getElementById("filter-search").value.toLowerCase();
  const sector = document.getElementById("filter-sector").value;
  const minScore = parseInt(document.getElementById("filter-score").value, 10);
  const maxMcapMio = parseInt(document.getElementById("filter-mcap").value, 10);

  return state.data.top_results.filter((r) => {
    if (search && !r.ticker.toLowerCase().includes(search) && !r.name.toLowerCase().includes(search)) return false;
    if (sector && r.sector !== sector) return false;
    if (r.total_score < minScore) return false;
    if (r.market_cap_usd > maxMcapMio * 1_000_000) return false;
    return true;
  });
}

function sortRows(rows) {
  const col = state.sortCol;
  const dir = state.sortDir === "asc" ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const av = a[col], bv = b[col];
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "string") return av.localeCompare(bv) * dir;
    return (av - bv) * dir;
  });
}

function refresh() {
  const rows = sortRows(getFilteredRows());
  renderTable(rows);
}

function populateSectorDropdown() {
  const select = document.getElementById("filter-sector");
  const sectors = [...new Set(state.data.top_results.map((r) => r.sector))].sort();
  sectors.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    select.appendChild(opt);
  });
}

["filter-search", "filter-sector"].forEach((id) => {
  document.getElementById(id).addEventListener("input", refresh);
});
document.getElementById("filter-score").addEventListener("input", (e) => {
  document.getElementById("score-val").textContent = e.target.value;
  refresh();
});
document.getElementById("filter-mcap").addEventListener("input", (e) => {
  document.getElementById("mcap-val").textContent = e.target.value;
  refresh();
});

document.querySelectorAll("#header-row th[data-col]").forEach((th) => {
  th.addEventListener("click", () => {
    const col = th.dataset.col;
    if (state.sortCol === col) {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    } else {
      state.sortCol = col;
      state.sortDir = "desc";
    }
    refresh();
  });
});
```

Also change the end of `load()` — replace:

```javascript
state.filteredRows = data.top_results.slice();
renderTable(state.filteredRows);
```

with:

```javascript
populateSectorDropdown();
refresh();
```

- [ ] **Step 3: Smoke-test filters and sorting**

Run:

```bash
cd dashboard && python -m http.server 8080
```

Open `http://localhost:8080`. Expected:
- Click on column headers → rows re-sort, second click flips direction.
- Type in search → rows filter.
- Move score slider → rows with lower score disappear, label updates.
- Move market cap slider → same for market cap.
- Sector dropdown populated with unique sector values from data.

- [ ] **Step 4: Commit**

```bash
git add dashboard/index.html
git commit -m "feat(dashboard): add filters and column sorting"
```

---

## Task 13: Dashboard — "How it Works" Explainer

**Files:**
- Modify: `dashboard/index.html`

- [ ] **Step 1: Add explainer modal content**

Inside the `<script>` block, add this function after `showDetail`:

```javascript
function showExplainer() {
  document.getElementById("modal-content").innerHTML = `
    <h2 class="text-2xl font-bold mb-3">Wie funktioniert der Screener?</h2>
    <p class="text-sm text-slate-700 mb-3">
      Dieser Screener sucht US-Aktien mit Marktkapitalisierung unter 500 Mio. USD,
      die den fünf wiederkehrenden Mustern aus Tony's Studie "An Analysis of 100-baggers" entsprechen.
    </p>
    <h3 class="font-semibold mt-3 mb-1">Hard-Filter (Titel muss alle erfüllen)</h3>
    <ul class="text-sm list-disc pl-5 text-slate-700">
      <li>Market Cap &lt; 500 Mio. USD</li>
      <li>Letztes Quartal (MRQ) EPS &gt; 0 (auch Turnaround-Kandidaten zulässig)</li>
      <li>Durchschn. Tagesvolumen &gt; 100.000 USD</li>
      <li>Mind. 8 Quartale Berichts-Historie</li>
      <li>US-Listing (NYSE, NASDAQ, AMEX)</li>
    </ul>
    <h3 class="font-semibold mt-3 mb-1">Scoring (max 100 Punkte)</h3>
    <ul class="text-sm list-disc pl-5 text-slate-700">
      <li><b>EPS-Wachstumsbeschleunigung (max 35):</b> Werden die yoy-Wachstumsraten der letzten 4 Quartale sequentiell größer?</li>
      <li><b>PEG-Ratio (max 25):</b> &lt; 0,5 = volle Punkte, &lt; 1,0 = halbe Punkte.</li>
      <li><b>Market Cap klein (max 15):</b> je kleiner, desto mehr Raum für 100-fach.</li>
      <li><b>Umsatzwachstum (max 15):</b> stützt die Qualität des EPS-Wachstums.</li>
      <li><b>Turnaround-Signal (max 10):</b> Bonus, wenn vor 2+ Jahren Verlust, jetzt profitabel UND beschleunigend.</li>
    </ul>
    <p class="text-xs text-slate-500 mt-4">
      Kein Investment-Ratschlag. Basis: Tony, "An Analysis of 100-baggers", tsanalysis.com.
    </p>
  `;
  document.getElementById("detail-modal").classList.remove("hidden");
}

document.getElementById("explainer-btn").addEventListener("click", showExplainer);
```

- [ ] **Step 2: Smoke-test explainer**

Run the dashboard as before. Click "Wie funktioniert der Screener?" → Modal mit Hard-Filter-Liste und Scoring-Erklärung erscheint. Schließen-Button funktioniert.

- [ ] **Step 3: Commit**

```bash
git add dashboard/index.html
git commit -m "feat(dashboard): add explainer modal"
```

---

## Task 14: README and Run Instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write project README**

Write to `README.md`:

```markdown
# 100-Bagger Screener

Ein monatlich aktualisierter Screener für US-Aktien unter 500 Mio. USD Market Cap, basierend auf den Mustern aus Tony's Studie *An Analysis of 100-baggers*.

## Setup

```bash
python -m venv venv
source venv/Scripts/activate  # Windows bash
pip install -r pipeline/requirements.txt
```

## Pipeline ausführen (monatlich)

```bash
python pipeline/run_pipeline.py
```

Dauer: ca. 30–60 Minuten für ~4.000-7.000 Ticker.
Output: `dashboard/data.json` + `pipeline/pipeline_log.txt`.

## Dashboard ansehen

```bash
cd dashboard && python -m http.server 8080
```

Browser öffnen: http://localhost:8080

Alternativ: `dashboard/` auf GitHub Pages oder Netlify deployen.

## Tests

```bash
pytest pipeline/tests/ -v
```

## Dokumentation

- Spec: `docs/superpowers/specs/2026-04-21-100bagger-screener-design.md`
- Plan: `docs/superpowers/plans/2026-04-21-100bagger-screener.md`
- Originalstudie: `100-baggers.md` / `100-baggers.pdf`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and run instructions"
```

---

## Task 15: Full Pipeline Test Run

**Files:** no new files; executes the real pipeline end-to-end.

This task is intentionally separate so the engineer can checkpoint before the ~30-60 min run.

- [ ] **Step 1: Run full pipeline**

```bash
python pipeline/run_pipeline.py
```

Expected: progress logs every 100 tickers. Final output:
- `dashboard/data.json` with `top_results` containing up to 50 companies.
- `pipeline/pipeline_log.txt` with passed/filtered/skipped counts.

Typical expectation:
- Universe size: 6.000–8.000 tickers from NASDAQ Trader.
- Skipped (missing data / errors): can be 50-70% — many tickers have thin data at that size.
- Passed hard filter: a few hundred.
- Top 50: the best-scoring ones.

- [ ] **Step 2: Open dashboard and verify**

```bash
cd dashboard && python -m http.server 8080
```

Open http://localhost:8080. Expected:
- Meta-line zeigt das Tagesdatum, Universum-Size, passierte Titel.
- 50 Zeilen in der Tabelle, oben hohe Scores (≥50).
- Filter und Sortierung funktionieren auf echten Daten.
- Klick auf Zeile → Detail-Modal mit realistischen Werten.

If scores look implausible (e.g., every top ticker has PEG=0), investigate `fetch.py` field mappings — `yfinance` returns occasionally change.

- [ ] **Step 3: Commit the generated data (optional)**

If you want a snapshot of the first real run in git:

```bash
git add dashboard/data.json pipeline/pipeline_log.txt
git commit -m "data: first full pipeline run"
```

Note: future runs will regenerate these files. They're committed as a reference but subsequent runs can either commit new snapshots or be gitignored — up to the user.

---

## Summary

After all 15 tasks complete, the project has:
- A tested Python pipeline that pulls US equity fundamentals, applies hard filters, and scores candidates across 5 criteria derived from Tony's study.
- A single-file HTML dashboard with sortable/filterable table, detail modal, and explainer.
- ~30 passing unit + integration tests.
- README and full documentation trail (spec + plan).

Total LOC estimate: ~600 lines Python, ~250 lines HTML/JS.

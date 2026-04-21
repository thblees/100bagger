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

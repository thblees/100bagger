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

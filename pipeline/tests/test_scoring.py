from scoring import eps_acceleration_score


def test_perfect_ladder_scores_35():
    # g_{-3}=0.05, g_{-2}=0.15, g_{-1}=0.30, g_0=0.50 — strictly increasing
    assert eps_acceleration_score([0.05, 0.15, 0.30, 0.50]) == 35


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

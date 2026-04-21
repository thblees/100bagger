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

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

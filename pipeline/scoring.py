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

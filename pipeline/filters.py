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

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

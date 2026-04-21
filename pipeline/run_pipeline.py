"""
Main orchestration: run the 100-bagger screener end-to-end.

Usage:
    python pipeline/run_pipeline.py

Output:
    docs/data.json
    pipeline/pipeline_log.txt
"""
import sys
import time
import traceback
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from universe import fetch_us_tickers
from fetch import fetch_fundamentals
from filters import passes_hard_filter
from scoring import score_company
from output import assemble_output, write_output


LOG_PATH = ROOT / "pipeline" / "pipeline_log.txt"
OUTPUT_PATH = ROOT / "docs" / "data.json"


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

"""
Apply the quality overlay to the existing docs/data.json top-50 and write
an annotated version (each row gets quality_pass + quality_reasons).

Run: venv/Scripts/python pipeline/rerank_quality.py
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quality import quality_pass

DATA_PATH = ROOT / "docs" / "data.json"


def main():
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows = payload["top_results"]
    print(f"Checking quality for {len(rows)} candidates...")

    for idx, row in enumerate(rows, 1):
        print(f"  [{idx}/{len(rows)}] {row['ticker']}... ", end="", flush=True)
        t0 = time.time()
        try:
            passed, reasons = quality_pass(row)
        except Exception as e:
            passed, reasons = False, [f"exception:{type(e).__name__}"]
        row["quality_pass"] = passed
        row["quality_reasons"] = reasons
        elapsed = time.time() - t0
        flag = "PASS" if passed else "FAIL"
        print(f"{flag} ({elapsed:.1f}s) {' '.join(reasons) if reasons else ''}")

    DATA_PATH.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    passed_rows = [r for r in rows if r["quality_pass"]]
    print()
    print(f"Quality-filtered: {len(passed_rows)} / {len(rows)} passed all gates")
    print()
    print("Top 10 quality-passed:")
    for r in sorted(passed_rows, key=lambda x: x["total_score"], reverse=True)[:10]:
        print(
            f"  {r['ticker']:6} score={r['total_score']:3} "
            f"mcap={r['market_cap_usd']/1e6:.0f}M "
            f"ttm_eps={r['ttm_eps']:.2f} "
            f"sector={r['sector']}"
        )


if __name__ == "__main__":
    main()

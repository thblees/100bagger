import json
from pathlib import Path


def assemble_output(
    scored_companies: list[dict],
    universe_size: int,
    passed_hard_filter: int,
    generated_at: str,
    top_n: int = 50,
) -> dict:
    """Sort scored companies by total_score desc, keep top N, build payload."""
    sorted_companies = sorted(
        scored_companies, key=lambda c: c["total_score"], reverse=True
    )
    top = sorted_companies[:top_n]
    return {
        "generated_at": generated_at,
        "universe_size": universe_size,
        "passed_hard_filter": passed_hard_filter,
        "top_results": top,
    }


def write_output(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

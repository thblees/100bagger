import json
from pathlib import Path

from output import assemble_output, write_output


def test_assemble_output_sorts_and_caps():
    scored = [
        {"ticker": "AAA", "total_score": 50},
        {"ticker": "BBB", "total_score": 80},
        {"ticker": "CCC", "total_score": 65},
    ]
    result = assemble_output(
        scored_companies=scored,
        universe_size=1000,
        passed_hard_filter=3,
        generated_at="2026-04-21",
        top_n=2,
    )
    assert result["generated_at"] == "2026-04-21"
    assert result["universe_size"] == 1000
    assert result["passed_hard_filter"] == 3
    assert len(result["top_results"]) == 2
    assert result["top_results"][0]["ticker"] == "BBB"
    assert result["top_results"][1]["ticker"] == "CCC"


def test_write_output_creates_valid_json(tmp_path: Path):
    payload = {"generated_at": "2026-04-21", "top_results": []}
    target = tmp_path / "data.json"
    write_output(payload, target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == payload

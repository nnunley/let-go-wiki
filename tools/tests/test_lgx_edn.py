import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_lgx_edn_defines_required_tasks():
    text = (ROOT / "lgx.edn").read_text(encoding="utf-8")
    for task in ("doctor", "viz", "build", "serve"):
        assert re.search(rf'\b{task}\b', text), f"missing task {task}"
    # Balanced braces — cheap EDN sanity check.
    assert text.count("{") == text.count("}")
    assert text.count("[") == text.count("]")

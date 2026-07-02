from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.status import render_status  # noqa: E402

def test_render_status_summarizes_counts():
    out = render_status({"total": 296, "authored": 5, "pending": ["clojure.core/filter"]})
    assert "5/296" in out
    assert "clojure.core/filter" in out

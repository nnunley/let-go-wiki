import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.coverage import page_path_for, authored_ids, coverage  # noqa: E402

def test_page_path_for_stdlib():
    assert page_path_for("clojure.core/map", "Function") == "references/clojure.core/map.md"
    assert page_path_for("clojure.core/when", "Macro") == "references/clojure.core/when.md"

def test_authored_ids_from_paths(tmp_path):
    (tmp_path / "references" / "clojure.core").mkdir(parents=True)
    (tmp_path / "references" / "clojure.core" / "map.md").write_text("x", encoding="utf-8")
    (tmp_path / "concepts").mkdir()
    (tmp_path / "concepts" / "indexed-rpn-ir.md").write_text("x", encoding="utf-8")
    ids = authored_ids(tmp_path)
    assert "clojure.core/map" in ids
    assert "indexed-rpn-ir" in ids

def test_coverage_reports_pending(tmp_path):
    (tmp_path / "references" / "clojure.core").mkdir(parents=True)
    (tmp_path / "references" / "clojure.core" / "map.md").write_text("x", encoding="utf-8")
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps([
        {"id": "clojure.core/map", "kind": "Function"},
        {"id": "clojure.core/filter", "kind": "Function"},
    ]), encoding="utf-8")
    cov = coverage(manifest, tmp_path)
    assert cov["total"] == 2 and cov["authored"] == 1
    assert cov["pending"] == ["clojure.core/filter"]

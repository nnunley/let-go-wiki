import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.prepare import prepare  # noqa: E402
from tools.letgo_source import resolve_lg  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

def test_prepare_writes_manifest_from_config(tmp_path):
    if resolve_lg() is None:
        pytest.skip("lg not available")
    # Point a temp config at the committed fixture, with source-root = repo root.
    cfg = tmp_path / "config.toml"
    cfg.write_text('[[source]]\nfile = "tools/tests/fixtures/sample.lg"\nns = "sample.core"\n',
                   encoding="utf-8")
    manifest = prepare(cfg, tmp_path / "work", ROOT)
    records = json.loads(Path(manifest).read_text(encoding="utf-8"))
    by = {r["name"]: r for r in records}
    assert by["square"]["signature"] == "(square [n])"
    assert by["square"]["kind"] == "Function"
    assert all(r["status"] == "pending" for r in records)
    assert by["square"]["doc"] == "Return n squared."


def test_prepare_deduplicates_manifest_by_id(tmp_path):
    if resolve_lg() is None:
        pytest.skip("lg not available")
    # Create a temp .lg file with duplicate definitions: def alias then defn real.
    lg_file = tmp_path / "duped.lg"
    lg_file.write_text(
        '(def dup dup*)\n'
        '(defn dup "Real one." [x] x)\n'
        '(def other-dup other-dup*)\n'
        '(defmacro other-dup "Real macro." [x] `x)\n',
        encoding="utf-8"
    )
    cfg = tmp_path / "config.toml"
    cfg.write_text(f'[[source]]\nfile = "duped.lg"\nns = "test.core"\n',
                   encoding="utf-8")
    manifest = prepare(cfg, tmp_path / "work", tmp_path)
    records = json.loads(Path(manifest).read_text(encoding="utf-8"))

    # Verify each id appears exactly once.
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), f"Duplicate ids found: {ids}"

    # Verify dup is a Function with signature and doc (not a Var with no args).
    by_name = {r["name"]: r for r in records}
    assert by_name["dup"]["id"] == "test.core/dup"
    assert by_name["dup"]["kind"] == "Function"
    assert by_name["dup"]["signature"] == "(dup [x])"
    assert by_name["dup"]["doc"] == "Real one."

    # Verify other-dup is a Macro with signature and doc.
    assert by_name["other-dup"]["id"] == "test.core/other-dup"
    assert by_name["other-dup"]["kind"] == "Macro"
    assert by_name["other-dup"]["signature"] == "(other-dup [x])"
    assert by_name["other-dup"]["doc"] == "Real macro."

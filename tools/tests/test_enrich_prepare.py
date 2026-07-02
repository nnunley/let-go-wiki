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

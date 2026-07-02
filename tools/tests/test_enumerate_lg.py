import json, shutil, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tools/tests/fixtures/sample.lg"

def _lg():
    if shutil.which("lg"):
        return ["lg"]
    if shutil.which("mise"):
        try:
            if subprocess.run(["mise","exec","--","lg","-e","nil"], cwd=ROOT,
                              capture_output=True, timeout=60).returncode == 0:
                return ["mise","exec","--","lg"]
        except (OSError, subprocess.SubprocessError):
            return None
    return None

def _run_enumerate():
    lg = _lg()
    if lg is None:
        pytest.skip("lg not available")
    script = ROOT / "tools/letgo/enumerate.lg"
    r = subprocess.run(lg + [str(script), str(FIX)], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    import re
    # enumerate.lg prints one EDN map per line; convert EDN-ish to python via a
    # tolerant parse: names/ops are strings, arglists are lists. The script emits
    # JSON (not EDN) to keep the Python side dependency-free — see Step 3.
    return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]

def test_enumerates_all_def_forms():
    forms = _run_enumerate()
    by_name = {f["name"]: f for f in forms}
    assert set(by_name) == {"square", "add", "answer", "unless", "helper"}

def test_defn_doc_and_arglist():
    f = next(f for f in _run_enumerate() if f["name"] == "square")
    assert f["op"] == "defn"
    assert f["doc"] == "Return n squared."
    assert f["arglists"] == [["n"]]

def test_multi_arity_arglists():
    f = next(f for f in _run_enumerate() if f["name"] == "add")
    assert f["arglists"] == [["a"], ["a", "b"]]
    assert f["doc"] is None

def test_def_and_macro_and_private():
    by = {f["name"]: f for f in _run_enumerate()}
    assert by["answer"]["op"] == "def"
    assert by["unless"]["op"] == "defmacro"
    assert by["helper"]["op"] == "defn-"
    assert by["helper"]["private"] is True

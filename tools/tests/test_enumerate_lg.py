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
    assert set(by_name) == {"square", "add", "answer", "unless", "helper", "tricky",
                            "*flag*", "masked"}

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

def test_metadata_reader_macro_on_name():
    """A ^:dynamic/^:private name reads as a (with-meta sym {...}) form; the
    enumerator must unwrap it to the bare symbol, not emit the whole form as the name."""
    by = {f["name"]: f for f in _run_enumerate()}
    assert "*flag*" in by, "^:dynamic def name was not unwrapped to its symbol"
    assert by["*flag*"]["op"] == "def"
    # ^:private in the metadata map must be detected as private.
    assert by["masked"]["private"] is True


def test_json_escape_control_chars():
    """Regression test: docstrings with newlines, quotes, backslashes, tabs must JSON-encode correctly."""
    f = next(f for f in _run_enumerate() if f["name"] == "tricky")
    # The docstring should contain actual newline, quote, backslash, and tab chars
    # after JSON decoding. This verifies the json-str helper escapes them correctly.
    expected_doc = 'Line one.\nHas a "quote", a back\\slash, and a\ttab.'
    assert f["doc"] == expected_doc

def test_real_core_lg_smoke_test():
    """Smoke test: enumerate on real core.lg must produce valid JSON for all lines.

    This catches real-data regressions that fixture-only tests cannot.
    Skips if core.lg is unavailable or lg is not available.
    """
    core_lg = ROOT / "../let-go/pkg/rt/core/core.lg"
    if not core_lg.exists():
        pytest.skip(f"core.lg not found at {core_lg}")

    lg = _lg()
    if lg is None:
        pytest.skip("lg not available")

    script = ROOT / "tools/letgo/enumerate.lg"
    r = subprocess.run(lg + [str(script), str(core_lg)], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"enumerate.lg failed: {r.stderr}"

    # Verify all lines are valid JSON
    forms = []
    for i, line in enumerate(r.stdout.strip().split('\n'), 1):
        if line.strip():
            try:
                forms.append(json.loads(line))
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i} is not valid JSON: {e}\n{line[:200]}")

    # core.lg should have > 100 def forms
    assert len(forms) > 100, f"Expected > 100 forms from core.lg, got {len(forms)}"

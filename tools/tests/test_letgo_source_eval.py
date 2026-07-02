from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from letgo_source import LetGoSource, Concept, resolve_lg  # noqa: E402

@pytest.fixture
def src():
    if resolve_lg() is None:
        pytest.skip("lg not available")
    return LetGoSource()

def test_signature_single_and_multi(src):
    c1 = Concept(id="x/square", kind="Function", name="square", ns="x",
                 arglists=[["n"]])
    assert src.read_concept(c1)["signature"] == "(square [n])"
    c2 = Concept(id="x/add", kind="Function", name="add", ns="x",
                 arglists=[["a"], ["a", "b"]])
    assert src.read_concept(c2)["signature"] == "(add [a] [a b])"

def test_eval_example_real_output(src):
    r = src.eval_example("(map inc [1 2 3])")
    assert r["error"] is None
    assert "(2 3 4)" in r["output"]

def test_eval_example_error_is_captured_not_raised(src):
    r = src.eval_example("(this-symbol-does-not-exist 1)")
    assert r["error"] is not None
    assert r["output"] == ""

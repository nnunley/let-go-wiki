from pathlib import Path
import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from letgo_source import LetGoSource, resolve_lg  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tools/tests/fixtures/sample.lg"

@pytest.fixture
def src():
    if resolve_lg() is None:
        pytest.skip("lg not available")
    return LetGoSource()

def test_list_concepts_kinds_and_ids(src):
    cs = {c.name: c for c in src.list_concepts(FIX, ns="sample.core")}
    assert cs["square"].kind == "Function"
    assert cs["square"].id == "sample.core/square"
    assert cs["unless"].kind == "Macro"
    assert cs["answer"].kind == "Var"
    assert cs["helper"].private is True

def test_private_functions_included_but_flagged(src):
    cs = {c.name: c for c in src.list_concepts(FIX, ns="sample.core")}
    assert set(cs) == {"square", "add", "answer", "unless", "helper", "tricky",
                       "*flag*", "masked"}
    assert cs["square"].arglists == [["n"]]
    assert cs["add"].arglists == [["a"], ["a", "b"]]
    # ^:private on the name (not defn-) must still flag the concept private.
    assert cs["masked"].private is True

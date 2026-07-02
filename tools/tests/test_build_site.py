from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_site import build, _nav, GRAPH_URL  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

def test_build_produces_styled_site(tmp_path):
    out = build(ROOT, tmp_path / "site")
    index = out / "index.html"
    assert index.exists()
    # House font is wired via the extra stylesheet.
    css_files = list(out.rglob("house*.css")) or list((out / "assets").rglob("*.css"))
    assert any("Boldonse" in c.read_text(encoding="utf-8") for c in css_files)
    # A content page rendered.
    assert (out / "entities" / "let-go" / "index.html").exists()

def test_nav_uses_full_relative_path_for_nested_pages(tmp_path):
    """Test that nested pages have the full relative path in nav, not just the filename."""
    docs = tmp_path / "docs"
    (docs / "references" / "clojure-compat").mkdir(parents=True)
    (docs / "references" / "clojure-compat" / "foo.md").write_text("x", encoding="utf-8")
    nav = _nav(docs)
    # flatten all page paths mentioned in nav
    flat = json.dumps(nav)
    assert "references/clojure-compat/foo.md" in flat

def test_nav_includes_graph_link(tmp_path):
    """The OKF graph is linked as an external nav entry."""
    nav = _nav(tmp_path / "docs")
    assert {"Graph ↗": GRAPH_URL} in nav
    assert GRAPH_URL.endswith("viz.html")


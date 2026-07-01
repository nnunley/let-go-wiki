import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "viz"))
from render_viz import render  # noqa: E402

def _page(p: Path, typ: str, title: str, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'---\ntype: {typ}\ncategory: {typ.lower()}\ntitle: "{title}"\n'
                 f'description: "d"\ntags: [go]\nstatus: stable\n---\n\n{body}\n', encoding="utf-8")

def test_render_produces_html_with_nodes(tmp_path):
    _page(tmp_path / "entities" / "let-go.md", "Entity", "let-go",
          "See [vm](../concepts/stack-vm.md).")
    _page(tmp_path / "concepts" / "stack-vm.md", "Concept", "Stack VM", "The VM.")
    out = tmp_path / "viz.html"
    stats = render(tmp_path, out, "test")
    assert out.exists()
    assert stats["concepts"] == 2
    html = out.read_text(encoding="utf-8")
    assert "#b45309" in html  # house accent present in restyled CSS

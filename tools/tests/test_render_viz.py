import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "viz"))
from render_viz import render  # noqa: E402

def _page(p: Path, typ: str, title: str, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'---\ntype: {typ}\ncategory: {typ.lower()}\ntitle: "{title}"\n'
                 f'description: "d"\ntags: [go]\nstatus: stable\n---\n\n{body}\n', encoding="utf-8")

def _doc(p: Path, title: str, body: str):
    """Write a doc with frontmatter but NO type field (like the design spec)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'---\ntitle: "{title}"\nstatus: draft\n---\n\n{body}\n', encoding="utf-8")

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

def test_render_excludes_non_content_docs(tmp_path):
    """Graph should exclude docs outside content dirs (e.g., design specs)."""
    # Create required index.md
    (tmp_path / "index.md").write_text("# Home\n", encoding="utf-8")

    # Create a content page (should be included)
    _page(tmp_path / "entities" / "x.md", "Entity", "Entity X", "An entity.")

    # Create a non-content doc with frontmatter (should be excluded)
    _doc(tmp_path / "docs" / "specs" / "design.md", "Design Spec", "A design spec.")

    out = tmp_path / "viz.html"
    stats = render(tmp_path, out, "test")

    # Should include only the entity, not the design spec
    assert stats["concepts"] == 1, f"Expected 1 concept, got {stats['concepts']}"

    html = out.read_text(encoding="utf-8")
    # "design" should not appear as a node id in the graph
    assert '"id":"docs/specs/design"' not in html
    assert "design" not in html.lower() or "design" not in html.split("__BUNDLE_DATA__")[1]

def test_graph_has_page_urls_and_rewritten_links(tmp_path):
    """Nodes should have MkDocs URLs; body .md links should be rewritten."""
    # Create two pages with cross-links
    _page(tmp_path / "entities" / "a.md", "Entity", "Entity A",
          "See [b](../concepts/b.md) for details.")
    _page(tmp_path / "concepts" / "b.md", "Concept", "Concept B", "The B concept.")

    out = tmp_path / "viz.html"
    stats = render(tmp_path, out, "test")
    assert stats["concepts"] == 2

    html = out.read_text(encoding="utf-8")

    # 1. Each node should have a "url" field pointing to MkDocs directory URL
    assert '"url": "entities/a/"' in html, "Node should have MkDocs directory URL"
    assert '"url": "concepts/b/"' in html, "Node should have MkDocs directory URL"

    # 2. Body links should be rewritten: [b](../concepts/b.md) -> [b](concepts/b/)
    # Check in the bodies section: no .md should appear in body links
    assert '[b](concepts/b/)' in html, "Body link should be rewritten to MkDocs URL"
    # Verify no .md appears in the markdown link in the body
    bodies_start = html.find('"bodies"')
    bodies_end = html.find('},"types"', bodies_start)
    bodies_section = html[bodies_start:bodies_end]
    # The rewritten link should NOT have .md
    assert 'b.md' not in bodies_section or '[b](../concepts/b.md)' not in bodies_section

def test_graph_has_home_link_and_open_page_button(tmp_path):
    """HTML should have home link and open-page affordance in detail panel."""
    _page(tmp_path / "entities" / "test.md", "Entity", "Test Entity", "Test body.")

    out = tmp_path / "viz.html"
    render(tmp_path, out, "test")

    html = out.read_text(encoding="utf-8")

    # 1. Header should have home link back to wiki
    assert '← let-go-wiki' in html, "Should have home link in header"
    assert 'href="."' in html, "Home link should navigate to site root"

    # 2. Detail panel should have "Open page" link
    assert 'Open page' in html, "Should have open-page affordance"
    assert 'class="open-page"' in html or 'open-page' in html.lower()

from pathlib import Path
import textwrap
from tools.check_wiki import (
    validate_page, extract_links, find_orphans, _letgo_url_problem)

REQUIRED = {"type", "category", "title", "description", "tags", "status"}

def _write(p: Path, fm: str, body: str = "Body.") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")
    return p

def test_valid_page_has_no_errors(tmp_path):
    p = _write(tmp_path / "entities" / "x.md", textwrap.dedent("""\
        type: Entity
        category: entity
        title: "X"
        description: "One sentence."
        tags: [go, vm]
        status: stable"""))
    assert validate_page(p) == []

def test_missing_required_key_is_reported(tmp_path):
    p = _write(tmp_path / "c.md", 'type: Concept\ncategory: concept\ntitle: "C"\ntags: [go]\nstatus: stable')
    errs = validate_page(p)
    assert any("description" in e for e in errs)

def test_absolute_link_is_reported(tmp_path):
    p = _write(tmp_path / "c.md",
               'type: Concept\ncategory: concept\ntitle: "C"\ndescription: "d"\ntags: [go]\nstatus: stable',
               body="See [x](/entities/x.md).")
    assert any("absolute link" in e for e in validate_page(p))

def test_unknown_tag_is_reported(tmp_path):
    p = _write(tmp_path / "c.md",
               'type: Concept\ncategory: concept\ntitle: "C"\ndescription: "d"\ntags: [not-a-real-tag]\nstatus: stable')
    assert any("tag" in e.lower() for e in validate_page(p))

def test_scalar_unknown_tag_is_reported(tmp_path):
    p = _write(tmp_path / "c.md",
               'type: Concept\ncategory: concept\ntitle: "C"\ndescription: "d"\ntags: not-a-real-tag\nstatus: stable')
    assert any("tag" in e.lower() for e in validate_page(p, tags={"go", "vm"}))

# NEW: Extract links via markdown parser
def test_extract_links_via_markdown_parser():
    md = "see [a](a.md) and [b](b.md) and <http://x> and [anchor](#section)"
    links = extract_links(md)
    assert "a.md" in links
    assert "b.md" in links
    assert "http://x" in links or "#section" in links or len(links) >= 2

# NEW: Broken relative link detection
def test_broken_relative_link_is_reported(tmp_path):
    p = _write(tmp_path / "concepts" / "page_a.md",
               'type: Concept\ncategory: concept\ntitle: "A"\ndescription: "d"\ntags: [go]\nstatus: stable',
               body="See [nope](nope.md).")
    errs = validate_page(p)
    assert any("broken link" in e for e in errs), f"Expected broken link error, got: {errs}"

# NEW: Valid relative link not reported
def test_valid_relative_link_not_reported(tmp_path):
    # Create page B
    _write(tmp_path / "concepts" / "page_b.md",
           'type: Concept\ncategory: concept\ntitle: "B"\ndescription: "d"\ntags: [go]\nstatus: stable')
    # Create page A that links to B
    p = _write(tmp_path / "concepts" / "page_a.md",
               'type: Concept\ncategory: concept\ntitle: "A"\ndescription: "d"\ntags: [go]\nstatus: stable',
               body="See [b](page_b.md).")
    errs = validate_page(p)
    assert not any("broken link" in e for e in errs), f"Should not report broken link for valid page, got: {errs}"

# NEW: Orphan detection
def test_find_orphans_reports_unlinked_pages(tmp_path):
    # Create index.md that links only to page_a
    _write(tmp_path / "index.md", "# Index", body="See [A](concepts/page_a.md).")
    # Create page A and page B
    _write(tmp_path / "concepts" / "page_a.md",
           'type: Concept\ncategory: concept\ntitle: "A"\ndescription: "d"\ntags: [go]\nstatus: stable')
    _write(tmp_path / "concepts" / "page_b.md",
           'type: Concept\ncategory: concept\ntitle: "B"\ndescription: "d"\ntags: [go]\nstatus: stable')
    orphans = find_orphans(tmp_path)
    # page_b should be in orphans (not linked from index or page_a)
    orphan_names = [str(o) for o in orphans]
    assert any("page_b" in o for o in orphan_names), f"Expected page_b to be orphan, got: {orphan_names}"

def test_find_orphans_empty_when_all_linked(tmp_path):
    # Create index.md that links to both pages
    _write(tmp_path / "index.md", "# Index", body="See [A](concepts/page_a.md) and [B](concepts/page_b.md).")
    # Create page A and page B
    _write(tmp_path / "concepts" / "page_a.md",
           'type: Concept\ncategory: concept\ntitle: "A"\ndescription: "d"\ntags: [go]\nstatus: stable')
    _write(tmp_path / "concepts" / "page_b.md",
           'type: Concept\ncategory: concept\ntitle: "B"\ndescription: "d"\ntags: [go]\nstatus: stable')
    orphans = find_orphans(tmp_path)
    assert len(orphans) == 0, f"Expected no orphans when all pages are linked, got: {orphans}"


def test_fragment_link_counts_as_inbound_for_orphans(tmp_path):
    """A page linked only via `page.md#section` must NOT be flagged orphan."""
    from tools.check_wiki import find_orphans
    (tmp_path / "_meta").mkdir(exist_ok=True)
    (tmp_path / "_meta" / "taxonomy.md").write_text("- `go`\n", encoding="utf-8")
    (tmp_path / "concepts").mkdir()
    b = tmp_path / "concepts" / "b.md"
    b.write_text("---\ntype: Concept\ncategory: concept\ntitle: \"B\"\n"
                 "description: \"d\"\ntags: [go]\nstatus: stable\n---\n\nB.\n", encoding="utf-8")
    # index links to B only with a fragment
    (tmp_path / "index.md").write_text("# Index\n\n- [B section](concepts/b.md#usage)\n", encoding="utf-8")
    assert find_orphans(tmp_path) == []


def test_generated_resource_is_flagged(tmp_path):
    """A resource/citation pointing at a generated artifact is flagged."""
    p = tmp_path / "c.md"
    p.write_text('---\ntype: Concept\ncategory: concept\ntitle: "C"\n'
                 'description: "d"\ntags: [go]\nstatus: stable\n'
                 'resource: "https://github.com/x/y/blob/main/pkg/ir/op_generated.go"\n'
                 '---\n\nBody.\n', encoding="utf-8")
    assert any("generated" in e for e in validate_page(p, tags={"go"}))

def test_source_resource_not_flagged(tmp_path):
    p = tmp_path / "c.md"
    p.write_text('---\ntype: Concept\ncategory: concept\ntitle: "C"\n'
                 'description: "d"\ntags: [go]\nstatus: stable\n'
                 'resource: "https://github.com/x/y/blob/main/pkg/ir/ir_ops.lg"\n'
                 '---\n\nBody.\n', encoding="utf-8")
    assert not any("generated" in e for e in validate_page(p, tags={"go"}))


# NEW: gitignored/non-public let-go URLs (static prefix rule — no repo needed)
def test_letgo_url_problem_flags_gitignored_prefix():
    url = ("https://github.com/nooga/let-go/blob/main/"
           "docs/superpowers/specs/2026-06-05-some-design.md")
    assert _letgo_url_problem(url, None) is not None

def test_letgo_url_problem_ignores_public_path():
    url = "https://github.com/nooga/let-go/blob/main/pkg/nrepl/server.go"
    assert _letgo_url_problem(url, None) is None

def test_letgo_url_problem_ignores_foreign_repo():
    # Only nooga/let-go URLs are governed by this rule.
    url = "https://github.com/other/repo/blob/main/docs/superpowers/x.md"
    assert _letgo_url_problem(url, None) is None

def test_private_letgo_resource_is_flagged_via_validate_page(tmp_path):
    p = tmp_path / "c.md"
    p.write_text('---\ntype: Concept\ncategory: concept\ntitle: "C"\n'
                 'description: "d"\ntags: [go]\nstatus: stable\n'
                 'resource: "https://github.com/nooga/let-go/blob/main/'
                 'docs/superpowers/plans/2026-06-29-x.md"\n'
                 '---\n\nBody.\n', encoding="utf-8")
    assert any("non-public" in e for e in validate_page(p, tags={"go"}))

def test_private_letgo_body_link_is_flagged(tmp_path):
    p = _write(tmp_path / "concepts" / "a.md",
               'type: Concept\ncategory: concept\ntitle: "A"\ndescription: "d"\n'
               'tags: [go]\nstatus: stable',
               body="See [design](https://github.com/nooga/let-go/tree/main/docs/superpowers).")
    assert any("non-public" in e for e in validate_page(p, tags={"go"}))

from pathlib import Path
import textwrap
from tools.check_wiki import validate_page

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

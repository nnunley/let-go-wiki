from pathlib import Path
import textwrap
from tools.check_wiki import (
    validate_page, extract_links, find_orphans, _letgo_url_problem, _letgo_ref,
    freshness_warnings)

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


# NEW: well-formedness checks
_OK_FM = ('type: Concept\ncategory: concept\ntitle: "C"\ndescription: "d"\n'
          'tags: [go]\nstatus: stable')

def test_bad_status_vocab_flagged(tmp_path):
    p = _write(tmp_path / "c.md", _OK_FM.replace("status: stable", "status: planning"))
    assert any("status 'planning'" in e for e in validate_page(p, tags={"go"}))

def test_bad_category_vocab_flagged(tmp_path):
    p = _write(tmp_path / "c.md", _OK_FM.replace("category: concept", "category: thing"))
    assert any("category 'thing'" in e for e in validate_page(p, tags={"go"}))

def test_unquoted_date_flagged(tmp_path):
    # Bare YAML date parses as a date object, not a string — flag it.
    p = _write(tmp_path / "c.md", _OK_FM + "\ncreated: 2026-07-02")
    assert any("created must be a quoted" in e for e in validate_page(p, tags={"go"}))

def test_quoted_date_not_flagged(tmp_path):
    p = _write(tmp_path / "c.md", _OK_FM + '\ncreated: "2026-07-02"')
    assert not any("created" in e for e in validate_page(p, tags={"go"}))

def test_duplicate_frontmatter_key_flagged(tmp_path):
    p = _write(tmp_path / "c.md", _OK_FM + "\ntags: [vm]")
    assert any("duplicate frontmatter key 'tags'" in e for e in validate_page(p, tags={"go", "vm"}))

def test_unbalanced_code_fence_flagged(tmp_path):
    p = _write(tmp_path / "concepts" / "c.md", _OK_FM, body="```python\nx = 1\n(no close)")
    assert any("code fence" in e for e in validate_page(p, tags={"go"}))

def test_multiline_description_flagged(tmp_path):
    fm = ('type: Concept\ncategory: concept\ntitle: "C"\n'
          'description: |\n  line one\n  line two\ntags: [go]\nstatus: stable')
    p = _write(tmp_path / "c.md", fm)
    assert any("description must be a single-line string" in e for e in validate_page(p, tags={"go"}))

def test_bad_type_vocab_flagged(tmp_path):
    p = _write(tmp_path / "c.md", _OK_FM.replace("type: Concept", "type: Thing"))
    assert any("type 'Thing'" in e for e in validate_page(p, tags={"go"}))

def test_source_type_not_flagged(tmp_path):
    # Every page under sources/ uses this, but AGENTS.md did not list it.
    p = _write(tmp_path / "c.md", _OK_FM.replace("type: Concept", "type: Source"))
    assert not any("type '" in e for e in validate_page(p, tags={"go"}))


# --- blob/main URLs are checked against the ref they name, not the worktree ---

def _git_repo(tmp_path: Path) -> Path:
    """A tiny git repo with a main branch and one tracked file."""
    import subprocess
    repo = tmp_path / "letgo"
    repo.mkdir()

    def run(*a):
        subprocess.run(a, cwd=repo, capture_output=True, check=True)

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "T")
    (repo / "pkg").mkdir()
    (repo / "pkg" / "kept.go").write_text("package kept\n", encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "seed")
    return repo

def test_letgo_ref_prefers_a_real_ref(tmp_path):
    assert _letgo_ref(_git_repo(tmp_path)) == "main"

def test_letgo_ref_is_none_without_one(tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    assert _letgo_ref(d) is None

def test_path_on_the_ref_is_accepted(tmp_path):
    repo = _git_repo(tmp_path)
    url = "https://github.com/nooga/let-go/blob/main/pkg/kept.go"
    assert _letgo_url_problem(url, repo) is None

def test_path_absent_from_the_ref_is_flagged(tmp_path):
    repo = _git_repo(tmp_path)
    url = "https://github.com/nooga/let-go/blob/main/pkg/gone.go"
    assert "no such path on main" in _letgo_url_problem(url, repo)

def test_untracked_worktree_file_does_not_satisfy_the_check(tmp_path):
    """The regression this change exists for.

    A file present on disk but absent from the ref used to pass, because the
    old check asked the filesystem. A citation to a path deleted upstream but
    still lying around locally would sail through.
    """
    repo = _git_repo(tmp_path)
    (repo / "pkg" / "local_only.go").write_text("package x\n", encoding="utf-8")
    url = "https://github.com/nooga/let-go/blob/main/pkg/local_only.go"
    assert _letgo_url_problem(url, repo) is not None


# --- freshness advisories: warn, never fail ------------------------------

REL = ("v1.13.0", "2026-09-20")

def test_freshness_ignores_non_stable_pages():
    fm = {"status": "speculative", "sources": ["no pin here"], "updated": "2026-01-01"}
    assert freshness_warnings(Path("c.md"), fm, REL) == []

def test_freshness_flags_a_stable_page_with_no_pin():
    fm = {"status": "stable", "sources": ["docs/guide/x.md"], "updated": "2026-09-21"}
    [note] = freshness_warnings(Path("c.md"), fm, REL)
    assert "no commit or release pin" in note

def test_a_sha_pin_satisfies_the_pin_check():
    fm = {"status": "stable", "sources": ["repo: x @ 36b13f79, 2026-09-20"],
          "updated": "2026-09-21"}
    assert freshness_warnings(Path("c.md"), fm, REL) == []

def test_a_release_pin_satisfies_the_pin_check():
    fm = {"status": "stable", "sources": ["lg 1.13.0 transcripts"], "updated": "2026-09-21"}
    assert freshness_warnings(Path("c.md"), fm, REL) == []

def test_freshness_flags_a_page_older_than_the_release():
    fm = {"status": "stable", "sources": ["repo: x @ 36b13f79"], "updated": "2026-07-02"}
    [note] = freshness_warnings(Path("c.md"), fm, REL)
    assert "before v1.13.0" in note

def test_both_reasons_collapse_to_one_line():
    """One note per page. Two notes per page across 40+ pages is a wall."""
    fm = {"status": "stable", "sources": ["nothing"], "updated": "2026-07-02"}
    notes = freshness_warnings(Path("c.md"), fm, REL)
    assert len(notes) == 1
    assert "no commit or release pin" in notes[0] and "before v1.13.0" in notes[0]

def test_freshness_is_silent_without_a_known_release():
    fm = {"status": "stable", "sources": ["repo: x @ 36b13f79"], "updated": "2026-07-02"}
    assert freshness_warnings(Path("c.md"), fm, None) == []

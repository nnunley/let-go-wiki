# let-go-wiki — Plan A: Scaffold & Tooling Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the let-go-wiki repo with its structure, house-styled published site, and OKF graph viewer — a working, deployable wiki on a couple of seed pages, driven through `lgx` tasks.

**Architecture:** A git repo of markdown+frontmatter pages (llm_wiki ⊕ OKF). A Python validator checks page conformance. A vendored, restyled OKF viewer emits a graph `viz.html`. `tools/build_site.py` stages content and runs MkDocs Material into `site/`, styled to match let-go's published page. `lgx.edn` fronts every tool as a task. GitHub Actions deploys `site/` to Pages. Content authoring (LetGoSource + enrich) is Plans B/C.

**Tech Stack:** Python 3.13, PyYAML, MkDocs + mkdocs-material, cytoscape/marked (CDN, in the vendored viewer), lgx (task runner), GitHub Pages.

## Global Constraints

- Python **3.13** for all `tools/` code (matches the vendored OKF viewer).
- Cross-links are **file-relative** `.md` links, never `/absolute`.
- Every non-reserved `.md` page carries dual frontmatter: required `type` **and** `category`, plus `title`, `description`, `tags`, `resource`, `sources`, `created`, `updated`, `status`.
- Tags come only from `_meta/taxonomy.md` (max 5 per page).
- Reserved files (`index.md`, `log.md`) carry no page frontmatter.
- The published site renders **only** content dirs (`concepts/ entities/ ideas/ projects/ sources/ references/`) + `index.md`; `tools/ _meta/ docs/ .claude/ AGENTS.md CLAUDE.md lgx.edn` are excluded from the site but tracked in git.
- House-style tokens (exact): `--serif:"Boldonse","Iowan Old Style",Georgia,serif`; `--mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace`; light `--bg:#f4ecdb --fg:#1d180f --muted:#877a5e --rule:#d6c8a8 --accent:#b45309`; dark `--bg:#1a1610 --fg:#ede1c4 --muted:#7a6d52 --rule:#34291c --accent:#f5b041`.
- Bookkeeping (`index.md`/`log.md`) uses direct markdown ops in this plan; llm-wiki CLI wiring is deferred.
- Repo already exists with `git`, `.gitignore` (root-md negations), and the committed spec. Do **not** re-`git init`.

---

## File Structure (created by this plan)

- `AGENTS.md` — canonical, model-agnostic maintenance instructions.
- `CLAUDE.md` — one-line pointer to AGENTS.md.
- `README.md` — what this repo is + how to build/serve.
- `_meta/taxonomy.md` — let-go tag vocabulary.
- `index.md`, `log.md` — catalog + chronological log.
- `concepts/ entities/ ideas/ projects/ sources/ references/` — content dirs (`.gitkeep` where empty).
- `entities/let-go.md`, `concepts/stack-vm.md` — seed pages.
- `tools/check_wiki.py` — frontmatter/link/tag validator.
- `tools/viz/` — vendored+restyled OKF viewer + `render_viz.py`.
- `tools/build_site.py` — stage content → MkDocs → `site/`.
- `tools/assets/css/house.css` — house-style overrides for Material.
- `mkdocs.base.yml` — MkDocs config template (build_site stages the rest).
- `tools/tests/` — pytest tests.
- `lgx.edn` — `doctor`/`viz`/`build`/`serve` tasks.
- `.github/workflows/pages.yml` — Pages deploy.
- `requirements.txt` — Python deps.

---

## Task 1: Repo scaffold — dirs, schema docs, taxonomy, index/log

**Files:**
- Create: `_meta/taxonomy.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `index.md`, `log.md`, `requirements.txt`
- Create: `concepts/.gitkeep`, `entities/.gitkeep`, `ideas/.gitkeep`, `projects/.gitkeep`, `sources/.gitkeep`, `references/.gitkeep`

**Interfaces:**
- Produces: the taxonomy tag set (used by `check_wiki.py` in Task 2 and every page); the dual-frontmatter contract documented in `AGENTS.md`.

- [ ] **Step 1: Create content dirs with keepers**

```bash
cd ~/development/let-go-wiki
mkdir -p concepts entities ideas projects sources references _meta tools/tests
for d in concepts entities ideas projects sources references; do touch "$d/.gitkeep"; done
```

- [ ] **Step 2: Write `_meta/taxonomy.md`**

```markdown
# Tag Taxonomy — let-go-wiki

Canonical tag vocabulary. Use only these tags; max 5 per page. Lowercase, hyphenated.
If no tag fits, add it here first.

## Domain
- `clojure` — Clojure language / semantics / compatibility
- `lisp` — Lisp / s-expression / macro topics
- `go` — Go language, Go interop, Go runtime
- `wasm` — WebAssembly build/runtime
- `vm` — the bytecode virtual machine
- `bytecode` — bytecode/compiler internals
- `compiler` — the let-go compiler
- `runtime` — runtime, persistent data structures, core.async
- `stdlib` — standard library / core namespaces / functions
- `interop` — Go ↔ let-go interop
- `tooling` — build/test/deps/project tooling (lgx, lginterop)
- `roguelike` — game / xsofy domain
- `graphics` — sixel / terminal / rendering (let-go-lab)

## Type
- `concept` — theory, mechanism, design
- `entity` — a tool, library, person, org, format
- `pattern` — reusable technique
- `reference` — external-sourced reference doc
- `project` — a program built with let-go
- `idea` — roadmap / speculative

## Status meaning (frontmatter `status`, not a tag)
`speculative` (agent draft) → `active` → `stable` (reviewed vs code) → `archived`.
```

- [ ] **Step 3: Write `AGENTS.md` (canonical schema/maintenance doc)**

```markdown
# Maintaining let-go-wiki (AGENTS.md)

This repo is an **LLM wiki** about developing and using **let-go** (a Clojure
dialect on a Go bytecode VM). It follows the llm_wiki pattern harmonized with
Google's Open Knowledge Format (OKF). Humans curate and ask; agents write and
maintain pages. This file is the canonical, model-agnostic schema — Claude,
Codex, Cursor, Gemini all read it (CLAUDE.md just points here).

## Page format (every non-reserved .md)

    ---
    type: Concept            # OKF-required; capitalized kind (Concept/Entity/Function/
                             #   Macro/Namespace/Package/Reference/Project/Idea)
    category: concept        # llm_wiki: concept|entity|idea|project|source|reference
    title: "Stack VM"
    description: "One sentence; used verbatim in index.md."
    tags: [vm, bytecode]     # from _meta/taxonomy.md, max 5
    resource: "https://github.com/nooga/let-go/tree/main/pkg/vm"  # source URI
    sources: ["repo: nooga/let-go pkg/vm, 2026-07-01"]
    created: "2026-07-01"
    updated: "2026-07-01"
    status: speculative      # speculative|active|stable|archived
    ---

- Cross-links are **file-relative** markdown links (`[stack vm](../concepts/stack-vm.md)`), never `/absolute`.
- `resource`/`sources` must cite where a claim comes from. Agent drafts start `speculative`; promote to `stable` only after checking against the actual code/runtime.

## Directories
`concepts/` (how it works / internals), `entities/` (the things),
`projects/` (programs built with let-go), `ideas/` (roadmap), `sources/`
(one page per ingested source), `references/` (OKF reference docs).

## Bookkeeping
- `index.md` = catalog by category; add one line per page: `[[path/slug]] — summary`.
- `log.md` = append-only; entries start `## [YYYY-MM-DD] <op> | <subject>`.
- Validate before commit: `python tools/check_wiki.py` (or `lgx doctor`).

## Build & publish
- `lgx doctor` — validate pages.  `lgx viz` — regenerate the graph.
- `lgx build` — build the styled site into `site/`.  `lgx serve` — local preview.
The site renders only content dirs + index.md; tooling/process files are excluded.
```

- [ ] **Step 4: Write `CLAUDE.md`, `README.md`, `index.md`, `log.md`, `requirements.txt`**

`CLAUDE.md`:
```markdown
See [AGENTS.md](AGENTS.md) — canonical, model-agnostic maintenance instructions for this wiki.
```

`README.md`:
```markdown
# let-go-wiki

A knowledge base for **developing and using** [let-go](https://github.com/nooga/let-go),
a Clojure dialect on a Go bytecode VM. Markdown + YAML frontmatter (llm_wiki ⊕ OKF),
agent-authored and agent-maintained, published as a styled static site.

## Use
- `lgx doctor` — validate pages against the schema
- `lgx viz` — regenerate the OKF graph (`viz.html`)
- `lgx build` — build the site into `site/`
- `lgx serve` — local preview

See [AGENTS.md](AGENTS.md) for the page format and conventions.
```

`index.md`:
```markdown
# let-go-wiki Index

Catalog of pages by category. Updated on every ingest.

## Entities
- [entities/let-go](entities/let-go.md) — the Clojure-dialect bytecode VM in Go.

## Concepts
- [concepts/stack-vm](concepts/stack-vm.md) — the stack-based bytecode virtual machine.

## Projects
*(none yet)*

## Ideas
*(none yet)*

## References
*(none yet)*

## Sources
*(none yet)*
```

`log.md`:
```markdown
# let-go-wiki Log

## [2026-07-01] init | scaffold
Created repo structure, taxonomy, schema docs (AGENTS.md/CLAUDE.md), and seed pages.
```

`requirements.txt`:
```
mkdocs==1.6.1
mkdocs-material==9.5.44
PyYAML==6.0.2
pytest==8.3.3
```

- [ ] **Step 5: Commit**

```bash
cd ~/development/let-go-wiki
git add -A
git commit -m "feat: scaffold wiki structure, taxonomy, and schema docs"
```

---

## Task 2: Page validator — `tools/check_wiki.py`

**Files:**
- Create: `tools/check_wiki.py`, `tools/tests/test_check_wiki.py`

**Interfaces:**
- Produces: `validate_page(path: Path) -> list[str]` (returns error strings; empty = valid) and `validate_tree(root: Path) -> dict[str, list[str]]` (path → errors). CLI `python tools/check_wiki.py [root]` exits non-zero if any errors. Consumed by `lgx doctor` (Task 6) and every later authoring task.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_check_wiki.py
from pathlib import Path
import textwrap
from tools.check_wiki import validate_page

REQUIRED = {"type", "category", "title", "description", "tags", "status"}

def _write(p: Path, fm: str, body: str = "Body.") -> Path:
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_check_wiki.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.check_wiki'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/check_wiki.py
"""Validate let-go-wiki pages: required frontmatter, relative links, known tags."""
from __future__ import annotations
import re, sys
from pathlib import Path
import yaml

REQUIRED_KEYS = ("type", "category", "title", "description", "tags", "status")
RESERVED = {"index.md", "log.md"}
_FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_ABS_LINK_RE = re.compile(r"\]\((/[^)]+\.md)\)")

def _load_taxonomy_tags(root: Path) -> set[str]:
    tax = root / "_meta" / "taxonomy.md"
    if not tax.exists():
        return set()
    return set(re.findall(r"^- `([a-z0-9-]+)`", tax.read_text(encoding="utf-8"), re.MULTILINE))

def _wiki_root(path: Path) -> Path:
    for p in [path, *path.parents]:
        if (p / "_meta" / "taxonomy.md").exists():
            return p
    return path.parent

def validate_page(path: Path, tags: set[str] | None = None) -> list[str]:
    if path.name in RESERVED:
        return []
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return [f"{path}: missing YAML frontmatter block"]
    errors: list[str] = []
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return [f"{path}: unparseable frontmatter: {e}"]
    for key in REQUIRED_KEYS:
        if key not in fm or fm[key] in (None, "", []):
            errors.append(f"{path}: missing/empty required key '{key}'")
    body = m.group(2)
    for lm in _ABS_LINK_RE.finditer(body):
        errors.append(f"{path}: absolute link '{lm.group(1)}' — use a file-relative link")
    known = tags if tags is not None else _load_taxonomy_tags(_wiki_root(path))
    page_tags = fm.get("tags") or []
    if isinstance(page_tags, list):
        if len(page_tags) > 5:
            errors.append(f"{path}: more than 5 tags")
        for t in page_tags:
            if known and t not in known:
                errors.append(f"{path}: unknown tag '{t}' (not in taxonomy)")
    return errors

def validate_tree(root: Path) -> dict[str, list[str]]:
    tags = _load_taxonomy_tags(root)
    content_dirs = ("concepts", "entities", "ideas", "projects", "sources", "references")
    out: dict[str, list[str]] = {}
    for d in content_dirs:
        for md in sorted((root / d).rglob("*.md")):
            errs = validate_page(md, tags)
            if errs:
                out[str(md.relative_to(root))] = errs
    return out

def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    results = validate_tree(root)
    if not results:
        print("check_wiki: OK")
        return 0
    for page, errs in results.items():
        for e in errs:
            print(e)
    return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_check_wiki.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/check_wiki.py tools/tests/test_check_wiki.py
git commit -m "feat: add page frontmatter/link/tag validator"
```

---

## Task 3: Seed pages that pass the validator

**Files:**
- Create: `entities/let-go.md`, `concepts/stack-vm.md`
- Test: `tools/tests/test_seed_pages.py`

**Interfaces:**
- Consumes: `validate_page` (Task 2). Produces: two conformant pages the viewer (Task 4) and site (Task 5) render.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_seed_pages.py
from pathlib import Path
from tools.check_wiki import validate_page, _load_taxonomy_tags

ROOT = Path(__file__).resolve().parents[2]

def test_seed_pages_are_valid():
    tags = _load_taxonomy_tags(ROOT)
    for rel in ("entities/let-go.md", "concepts/stack-vm.md"):
        assert validate_page(ROOT / rel, tags) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_seed_pages.py -v`
Expected: FAIL — files do not exist (`FileNotFoundError`).

- [ ] **Step 3: Create the seed pages**

`entities/let-go.md`:
```markdown
---
type: Entity
category: entity
title: "let-go"
description: "A Clojure dialect with a bytecode compiler and stack VM, written in Go."
tags: [clojure, go, vm, wasm]
resource: "https://github.com/nooga/let-go"
sources: ["repo: nooga/let-go README, 2026-07-01"]
created: "2026-07-01"
updated: "2026-07-01"
status: stable
---

# let-go

let-go is a Clojure dialect implemented as a bytecode compiler and stack-based
virtual machine in Go. It produces a single ~12MB binary with ~8ms cold start,
no JVM, and passes the jank-lang Clojure test suite. It supports AOT compilation
to standalone binaries and self-contained WASM web pages, two-way Go interop, and
most of Clojure (persistent data structures, lazy seqs, transducers, protocols,
records, multimethods, core.async, BigInts).

See the [stack VM](../concepts/stack-vm.md) for how compiled bytecode executes.

# Citations

[1] [let-go repository](https://github.com/nooga/let-go)
```

`concepts/stack-vm.md`:
```markdown
---
type: Concept
category: concept
title: "Stack VM"
description: "The stack-based virtual machine that executes let-go bytecode."
tags: [vm, bytecode, runtime]
resource: "https://github.com/nooga/let-go/tree/main/pkg/vm"
sources: ["repo: nooga/let-go pkg/vm, 2026-07-01"]
created: "2026-07-01"
updated: "2026-07-01"
status: speculative
---

# Stack VM

The let-go compiler emits bytecode that runs on a stack-based virtual machine.
Values are pushed and popped from an operand stack; instructions operate on the
top of the stack. This is the execution substrate for [let-go](../entities/let-go.md)
programs after compilation.

> status: speculative — verify details against `pkg/vm` before promoting to stable.

# Citations

[1] [pkg/vm](https://github.com/nooga/let-go/tree/main/pkg/vm)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_seed_pages.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add entities/let-go.md concepts/stack-vm.md tools/tests/test_seed_pages.py
git commit -m "feat: add seed pages for let-go and stack-vm"
```

---

## Task 4: Vendor + restyle the OKF graph viewer

**Files:**
- Create: `tools/viz/generator.py` (vendored + patched), `tools/viz/templates/viz.html`, `tools/viz/static/*` (vendored), `tools/viz/render_viz.py`, `tools/viz/__init__.py`
- Test: `tools/tests/test_render_viz.py`

**Interfaces:**
- Consumes: a directory of frontmatter'd `.md`. Produces: `render_viz.render(bundle_root: Path, out: Path, name: str) -> dict` writing `out` (self-contained HTML) and returning `{"concepts": int, "edges": int}`. CLI `python tools/viz/render_viz.py <root> [out]`. Consumed by `lgx viz` (Task 6).

- [ ] **Step 1: Vendor the viewer files from the cloned repo**

```bash
cd ~/development/let-go-wiki
KC=/private/tmp/claude-501/-Users-ndn-development-let-go-wiki/d4bf016b-09dd-44ce-b4c4-496559b95922/scratchpad/kc
mkdir -p tools/viz
cp "$KC/okf/src/reference_agent/viewer/generator.py" tools/viz/generator.py
cp -r "$KC/okf/src/reference_agent/viewer/templates" tools/viz/templates
cp -r "$KC/okf/src/reference_agent/viewer/static" tools/viz/static
touch tools/viz/__init__.py
```

- [ ] **Step 2: Patch out the `reference_agent` dependency in `generator.py`**

Replace the import line and the parse call so the viewer has no external package dep. In `tools/viz/generator.py`:

Replace:
```python
from reference_agent.bundle.document import OKFDocument, OKFDocumentError
```
with:
```python
import yaml

class OKFDocumentError(Exception):
    pass

class OKFDocument:
    def __init__(self, frontmatter, body):
        self.frontmatter = frontmatter
        self.body = body

    @staticmethod
    def parse(text: str) -> "OKFDocument":
        import re
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
        if not m:
            raise OKFDocumentError("no frontmatter")
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            raise OKFDocumentError(str(e))
        return OKFDocument(fm, m.group(2))
```

- [ ] **Step 3: Add let-go type colors + house accent**

In `tools/viz/generator.py`, replace the `_TYPE_PALETTE` / `_DEFAULT_NODE_COLOR` block with:
```python
_TYPE_PALETTE = {
    "Entity": "#b45309",
    "Concept": "#877a5e",
    "Reference": "#10b981",
    "Project": "#3b82f6",
    "Idea": "#8b5cf6",
    "Function": "#877a5e",
    "Macro": "#877a5e",
    "Namespace": "#b45309",
    "Package": "#3b82f6",
}
_DEFAULT_NODE_COLOR = "#877a5e"
```

- [ ] **Step 4: Restyle the viewer CSS to house tokens**

Overwrite `tools/viz/static/` CSS with house style. First find the CSS asset:
```bash
ls tools/viz/static
```
Then overwrite the `.css` file it lists (referred to here as `tools/viz/static/viz.css`) with:
```css
:root{
  --bg:#f4ecdb; --fg:#1d180f; --muted:#877a5e; --rule:#d6c8a8; --accent:#b45309;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
  --serif:"Boldonse","Iowan Old Style",Georgia,serif;
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#1a1610; --fg:#ede1c4; --muted:#7a6d52; --rule:#34291c; --accent:#f5b041; }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--mono);display:flex;flex-direction:column;height:100vh}
header{display:flex;justify-content:space-between;align-items:center;padding:.6rem 1rem;border-bottom:1px solid var(--rule)}
header .title strong{font-family:var(--serif)}
.muted{color:var(--muted)}
.controls input,.controls select,.controls button{font-family:var(--mono);background:transparent;color:var(--fg);border:1px solid var(--rule);border-radius:4px;padding:.3rem .5rem;margin-left:.4rem}
.controls button:hover{border-color:var(--accent);color:var(--accent)}
main{display:flex;flex:1;min-height:0}
#graph{flex:2;min-width:0}
#detail{flex:1;max-width:420px;border-left:1px solid var(--rule);padding:1rem;overflow:auto}
#detail h1{font-family:var(--serif);color:var(--accent);font-size:1.2rem}
.type-chip{display:inline-block;padding:.1rem .4rem;border:1px solid var(--rule);border-radius:4px;color:var(--muted);font-size:.72rem}
.frontmatter dt{color:var(--muted);font-size:.72rem;letter-spacing:.04em;margin-top:.5rem}
a{color:var(--accent)}
hr{border:0;border-top:1px solid var(--rule)}
```
(If the listed CSS filename differs, overwrite that file instead — the loader reads whatever is in `static/`.)

- [ ] **Step 5: Write the wrapper `tools/viz/render_viz.py`**

```python
# tools/viz/render_viz.py
"""Standalone wrapper around the vendored OKF viewer (no GCP/reference_agent deps)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator import generate_visualization  # noqa: E402

def render(bundle_root: Path, out: Path, name: str = "let-go-wiki") -> dict:
    return generate_visualization(Path(bundle_root), Path(out), bundle_name=name)

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: render_viz.py <bundle_root> [out.html]", file=sys.stderr)
        return 2
    root = Path(argv[1])
    out = Path(argv[2]) if len(argv) > 2 else root / "viz.html"
    stats = render(root, out)
    print(f"viz: {stats.get('concepts', 0)} concepts, {stats.get('edges', 0)} edges -> {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 6: Write the failing test**

```python
# tools/tests/test_render_viz.py
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
```

- [ ] **Step 7: Run test to verify it fails, then passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_render_viz.py -v`
Expected first run: FAIL if the CSS/patches are incomplete. Apply Steps 2–4 until:
Expected: PASS (`stats["concepts"] == 2`, accent present).

- [ ] **Step 8: Commit**

```bash
git add tools/viz tools/tests/test_render_viz.py
git commit -m "feat: vendor and restyle OKF graph viewer (house style, no cloud deps)"
```

---

## Task 5: House-styled MkDocs site build — `tools/build_site.py`

**Files:**
- Create: `mkdocs.base.yml`, `tools/assets/css/house.css`, `tools/build_site.py`
- Test: `tools/tests/test_build_site.py`

**Interfaces:**
- Consumes: content dirs + `index.md`. Produces: `build_site.build(root: Path, out: Path) -> Path` (stages content into a temp `docs_dir`, writes a merged `mkdocs.yml`, runs `mkdocs build -d <out>`), returning the site dir. CLI `python tools/build_site.py [--serve]`. Consumed by `lgx build`/`lgx serve` (Task 6).

- [ ] **Step 1: Write `mkdocs.base.yml`**

```yaml
site_name: let-go-wiki
site_description: Developing and using let-go — a Clojure dialect on a Go bytecode VM.
theme:
  name: material
  font:
    text: JetBrains Mono
    code: JetBrains Mono
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle: { icon: material/weather-night, name: Dark }
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle: { icon: material/weather-sunny, name: Light }
  features: [navigation.sections, navigation.top, search.suggest, content.code.copy]
extra_css: [assets/css/house.css]
markdown_extensions:
  - admonition
  - pymdownx.superfences
  - toc: { permalink: true }
```

- [ ] **Step 2: Write `tools/assets/css/house.css` (map Material vars to let-go tokens)**

```css
@import url('https://fonts.googleapis.com/css2?family=Boldonse&family=JetBrains+Mono:wght@400;500&display=swap');

[data-md-color-scheme="default"]{
  --md-default-bg-color:#f4ecdb; --md-default-fg-color:#1d180f;
  --md-default-fg-color--light:#877a5e; --md-typeset-color:#1d180f;
  --md-primary-fg-color:#b45309; --md-accent-fg-color:#b45309;
  --md-typeset-a-color:#b45309;
}
[data-md-color-scheme="slate"]{
  --md-default-bg-color:#1a1610; --md-default-fg-color:#ede1c4;
  --md-default-fg-color--light:#7a6d52; --md-typeset-color:#ede1c4;
  --md-primary-fg-color:#f5b041; --md-accent-fg-color:#f5b041;
  --md-typeset-a-color:#f5b041;
}
.md-typeset h1,.md-typeset h2,.md-typeset h3{
  font-family:"Boldonse","Iowan Old Style",Georgia,serif; color:var(--md-accent-fg-color);
}
body,.md-typeset{ font-family:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace; }
```

- [ ] **Step 3: Write the failing test**

```python
# tools/tests/test_build_site.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_site import build  # noqa: E402

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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && pip install -r requirements.txt && python -m pytest tools/tests/test_build_site.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_site'`.

- [ ] **Step 5: Write `tools/build_site.py`**

```python
# tools/build_site.py
"""Stage content dirs into a MkDocs docs_dir and build the styled site."""
from __future__ import annotations
import shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

CONTENT_DIRS = ("concepts", "entities", "ideas", "projects", "sources", "references")
_TITLE_CAT = {"concepts": "Concepts", "entities": "Entities", "ideas": "Ideas",
              "projects": "Projects", "sources": "Sources", "references": "References"}

def _stage(root: Path, docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "index.md", docs_dir / "index.md")
    for d in CONTENT_DIRS:
        src = root / d
        if any(src.rglob("*.md")):
            shutil.copytree(src, docs_dir / d, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".gitkeep"))
    # Assets for extra_css.
    shutil.copytree(root / "tools" / "assets", docs_dir / "assets", dirs_exist_ok=True)

def _nav(docs_dir: Path) -> list:
    nav: list = [{"Home": "index.md"}]
    for d in CONTENT_DIRS:
        dd = docs_dir / d
        if not dd.exists():
            continue
        pages = [f"{d}/{p.name}" for p in sorted(dd.rglob("*.md"))]
        if pages:
            nav.append({_TITLE_CAT[d]: pages})
    return nav

def build(root: Path, out: Path) -> Path:
    root, out = Path(root), Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        docs_dir = tmp / "docs"
        _stage(root, docs_dir)
        base = yaml.safe_load((root / "mkdocs.base.yml").read_text(encoding="utf-8"))
        base["docs_dir"] = str(docs_dir)
        base["site_dir"] = str(out)
        base["nav"] = _nav(docs_dir)
        cfg = tmp / "mkdocs.yml"
        cfg.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
        subprocess.run(["mkdocs", "build", "-f", str(cfg), "--strict"],
                       check=True, cwd=root)
    return out

def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    if "--serve" in argv:
        # Stage once and serve for local preview.
        tmp = Path(tempfile.mkdtemp())
        _stage(root, tmp / "docs")
        base = yaml.safe_load((root / "mkdocs.base.yml").read_text(encoding="utf-8"))
        base["docs_dir"] = str(tmp / "docs"); base["nav"] = _nav(tmp / "docs")
        (tmp / "mkdocs.yml").write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
        return subprocess.run(["mkdocs", "serve", "-f", str(tmp / "mkdocs.yml")], cwd=root).returncode
    out = build(root, root / "site")
    print(f"site -> {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_build_site.py -v`
Expected: PASS (site/index.html + content page rendered; Boldonse present in copied CSS).

- [ ] **Step 7: Commit**

```bash
git add mkdocs.base.yml tools/assets tools/build_site.py tools/tests/test_build_site.py requirements.txt
git commit -m "feat: house-styled MkDocs site build with staged content"
```

---

## Task 6: `lgx.edn` — front every tool as a task

**Files:**
- Create: `lgx.edn`
- Test: `tools/tests/test_lgx_edn.py`

**Interfaces:**
- Consumes: `tools/check_wiki.py`, `tools/viz/render_viz.py`, `tools/build_site.py`. Produces: `lgx doctor|viz|build|serve` tasks. (Tasks shell out to Python so they work before the let-go migration.)

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_lgx_edn.py
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_lgx_edn_defines_required_tasks():
    text = (ROOT / "lgx.edn").read_text(encoding="utf-8")
    for task in ("doctor", "viz", "build", "serve"):
        assert re.search(rf'\b{task}\b', text), f"missing task {task}"
    # Balanced braces — cheap EDN sanity check.
    assert text.count("{") == text.count("}")
    assert text.count("[") == text.count("]")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_lgx_edn.py -v`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Write `lgx.edn`**

```clojure
{:paths ["src"]
 :tasks {"doctor" {:doc "Validate wiki pages against the schema"
                   :shell "python tools/check_wiki.py ."}
         "viz"    {:doc "Regenerate the OKF graph (viz.html)"
                   :shell "python tools/viz/render_viz.py . viz.html"}
         "build"  {:doc "Build the styled static site into site/"
                   :shell "python tools/build_site.py"}
         "serve"  {:doc "Local preview of the site"
                   :shell "python tools/build_site.py --serve"}}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_lgx_edn.py -v`
Expected: PASS

- [ ] **Step 5: Verify the task runner end-to-end (best effort)**

Run: `cd ~/development/let-go-wiki && (command -v lgx >/dev/null && lgx doctor || python tools/check_wiki.py .)`
Expected: `check_wiki: OK`. (If `lgx` is not installed, the Python fallback proves the underlying task; note lgx install as a follow-up.)

- [ ] **Step 6: Commit**

```bash
git add lgx.edn tools/tests/test_lgx_edn.py
git commit -m "feat: add lgx.edn tasks (doctor/viz/build/serve)"
```

---

## Task 7: GitHub Pages deploy workflow

**Files:**
- Create: `.github/workflows/pages.yml`
- Test: `tools/tests/test_pages_workflow.py`

**Interfaces:**
- Produces: CI that builds `site/` and deploys to Pages on push to the default branch.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_pages_workflow.py
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

def test_pages_workflow_is_valid_and_deploys():
    wf = yaml.safe_load((ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8"))
    assert "jobs" in wf
    steps = wf["jobs"]["build"]["steps"]
    text = yaml.safe_dump(wf)
    assert "actions/deploy-pages" in text
    assert "python tools/build_site.py" in text or "mkdocs build" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_pages_workflow.py -v`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Write `.github/workflows/pages.yml`**

```yaml
name: Deploy site to Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install -r requirements.txt
      - run: python tools/check_wiki.py .
      - run: python tools/build_site.py
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_pages_workflow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/pages.yml tools/tests/test_pages_workflow.py
git commit -m "ci: add GitHub Pages deploy workflow"
```

---

## Task 8: End-to-end wire-up — build artifacts, refresh bookkeeping

**Files:**
- Modify: `index.md`, `log.md`
- Create: `viz.html` (generated, committed for convenience)

**Interfaces:**
- Consumes: all prior tasks. Produces: a green full test run, a built site, and a committed graph.

- [ ] **Step 1: Run the full test suite**

Run: `cd ~/development/let-go-wiki && python -m pytest tools -v`
Expected: PASS (all tests across check_wiki, seed_pages, render_viz, build_site, lgx_edn, pages_workflow).

- [ ] **Step 2: Validate, build the graph and the site**

Run:
```bash
cd ~/development/let-go-wiki
python tools/check_wiki.py .
python tools/viz/render_viz.py . viz.html
python tools/build_site.py
```
Expected: `check_wiki: OK`; `viz: 2 concepts ...`; `site -> .../site`.

- [ ] **Step 3: Append a log entry**

Add to `log.md`:
```markdown
## [2026-07-01] build | tooling foundation
Added validator, restyled OKF viewer, MkDocs house-style site, lgx tasks, Pages CI.
Built viz.html and site/ from the two seed pages.
```

- [ ] **Step 4: Commit (site/ stays gitignored; viz.html is tracked)**

```bash
cd ~/development/let-go-wiki
git add viz.html log.md index.md
git commit -m "chore: build graph + refresh log for tooling foundation"
```

- [ ] **Step 5: Final verification**

Run: `cd ~/development/let-go-wiki && git status --short && python -m pytest tools -q`
Expected: clean tree (except gitignored `site/`), all tests pass.

---

## Self-Review

**Spec coverage (Plan A slice):** repo/structure (§4) → Task 1; harmonized frontmatter + relative links (§3) → Tasks 1–3 + validator; maintenance validator/`AGENTS.md` model-agnostic (§2, §6) → Tasks 1–2; vendored+restyled OKF viewer (§6, §8) → Task 4; styled GitHub Pages site with house tokens (§8) → Tasks 5,7; lgx task front (§6, §9) → Task 6; multi-party git hygiene (§2.1) → pre-existing `.gitignore` (verified earlier). Deferred to Plans B/C: `LetGoSource`, enrich passes, population/review, WASM playground, llm-wiki CLI wiring — all explicitly out of Plan A scope.

**Placeholders:** none — every code step has complete content. The one runtime lookup (the exact CSS filename under `tools/viz/static/`) is handled by an explicit `ls` + "overwrite that file" instruction in Task 4 Step 4.

**Type consistency:** `validate_page(path, tags=None)` / `validate_tree(root)` used consistently (Tasks 2,3); `render(bundle_root, out, name)` returns `{"concepts","edges"}` used in Task 4 test and Task 8; `build(root, out)` returns the site dir, used in Task 5 test and Task 8.

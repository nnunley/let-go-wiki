# let-go-wiki — Plan C: Population & Review Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive the Plan B engine to actually author, validate, review, and publish wiki pages — building the population tooling (coverage / batch selection) with TDD, then running the agent-driven authoring loop for a first real batch of stdlib concepts, the Indexed-RPN IR internals page, and the first project case study.

**Architecture:** Two halves. (1) **Deterministic tooling** (TDD Python): map concept ids → page paths, report coverage (manifest ↔ existing pages), and generate per-concept *authoring briefs* (`enrich next`). (2) **Agent-driven population** (executed by dispatching one Claude authoring subagent per concept/page using the Plan B prompts): each subagent reads its brief, evaluates real examples via `lg -e`, writes a `check_wiki`-valid page, and the loop validates + reviews + promotes + publishes. Full coverage is reached by re-running the loop (this plan proves it end-to-end on a first batch + establishes the runbook).

**Tech Stack:** Python 3.13 + pytest, the Plan B engine (`LetGoSource`, `enrich prepare` manifest), `tools/check_wiki.py`, `lg`, MkDocs/Pages, Claude authoring subagents.

## Global Constraints

- Python **3.13**; deps pinned; tests run from repo root (`python -m pytest tools -q`); lg-dependent tests SKIP when `lg`/`../let-go` absent.
- Every authored page MUST pass `python tools/check_wiki.py .` (dual frontmatter, file-relative `.md` links, tags ⊆ `_meta/taxonomy.md` ≤5) and MUST NOT collide with an existing page id.
- Pages start `status: speculative`; promote to `stable` only after review against the actual code/runtime.
- `# Examples` MUST use **real `lg -e` output** — never invented (Plan B prompt rule).
- **External references:** internals/reference pages MUST include a `# Citations` section linking external sources where they exist (papers, other-language IRs, upstream docs) in addition to the `resource` source path.
- **Required deliverable (this plan):** a `concepts/indexed-rpn-ir.md` page documenting let-go's IR. **Precision (do not conflate):** indexed-RPN is **not** SSA — it is an SSA-*equivalent* representation: the positional/indexed RPN (postfix) encoding gives values their identity by position, so you get SSA-like value numbering *without* explicit SSA names. let-go's IR combines that indexed-RPN *encoding* with a *block-parameter* control-flow structure (the SSA-style channel is block args). The page must keep these two distinct. Cite the canonical external references (from `let-go/pkg/ir/op_generated.go`): Burak Emir, "Indexed Reverse Polish Notation" (burakemir.ch) — the indexed-RPN idea; Carbon semantic IR (`toolchain/sem_ir`); Swift SIL / Cranelift / MLIR (the block-parameter form). `resource` = `pkg/ir/op_generated.go` (+ `pkg/ir/ir_ops.lg`).
- **Page-path conventions** (deterministic, see Task 1): stdlib concept id `<ns>/<name>` → `reference/<ns>/<name>.md`; internals concepts → `concepts/<slug>.md`; projects → `projects/<name>.md`; entities → `entities/<name>.md`.
- Generated artifacts (`.enrich/`, `site/`) are NOT committed; `viz.html` IS committed (per the Plan A decision).
- Reuse existing tooling; the Plan B manifest (`.enrich/manifest.json`, 296 deduped concepts) is the stdlib work-list.

---

## File Structure (created/modified by this plan)

- `tools/enrich/coverage.py` — `page_path_for(id, kind)`, `authored_ids(root)`, `coverage(manifest, root)`; the manifest↔pages reconciliation.
- `tools/enrich/status.py` — `enrich status` CLI (coverage report). Wired to `lgx`/`make`.
- `tools/enrich/next_batch.py` — `enrich next --count N` — select un-authored concepts, write authoring briefs.
- `tools/tests/test_*.py` — TDD for the above.
- `reference/<ns>/<name>.md` — stdlib concept pages (authored, agent-driven).
- `concepts/indexed-rpn-ir.md` — the internals worked example (authored).
- `projects/xsofy.md` (+ `entities/xsofy.md` refinement) — first project case study (authored).
- `lgx.edn`, `Makefile` — add `status` / `next` tasks; update `test_lgx_edn.py`.
- `index.md`, `log.md`, `viz.html` — bookkeeping/artifacts refreshed at publish.

---

## Task 1: Coverage tooling — id↔page reconciliation

**Files:**
- Create: `tools/enrich/coverage.py`
- Test: `tools/tests/test_coverage.py`

**Interfaces:**
- Produces:
  - `page_path_for(concept_id: str, kind: str) -> str` — stdlib ids (`kind` in Function/Macro/Var) → `reference/<id>.md`; returns a repo-relative POSIX path.
  - `authored_ids(root: Path) -> set[str]` — scans `reference/`, `concepts/`, `projects/`, `entities/` for `.md` pages and returns the set of ids they cover. A page's id comes from its frontmatter `resource`? No — from its path: `reference/clojure.core/map.md` → `clojure.core/map`; `concepts/indexed-rpn-ir.md` → `indexed-rpn-ir`. Return the path-derived id (relative to its content dir, without `.md`).
  - `coverage(manifest_path: Path, root: Path) -> dict` → `{"total": int, "authored": int, "pending": list[str]}` where `pending` = manifest ids whose `reference/<id>.md` does not exist.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_coverage.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.coverage import page_path_for, authored_ids, coverage  # noqa: E402

def test_page_path_for_stdlib():
    assert page_path_for("clojure.core/map", "Function") == "reference/clojure.core/map.md"
    assert page_path_for("clojure.core/when", "Macro") == "reference/clojure.core/when.md"

def test_authored_ids_from_paths(tmp_path):
    (tmp_path / "reference" / "clojure.core").mkdir(parents=True)
    (tmp_path / "reference" / "clojure.core" / "map.md").write_text("x", encoding="utf-8")
    (tmp_path / "concepts").mkdir()
    (tmp_path / "concepts" / "indexed-rpn-ir.md").write_text("x", encoding="utf-8")
    ids = authored_ids(tmp_path)
    assert "clojure.core/map" in ids
    assert "indexed-rpn-ir" in ids

def test_coverage_reports_pending(tmp_path):
    (tmp_path / "reference" / "clojure.core").mkdir(parents=True)
    (tmp_path / "reference" / "clojure.core" / "map.md").write_text("x", encoding="utf-8")
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps([
        {"id": "clojure.core/map", "kind": "Function"},
        {"id": "clojure.core/filter", "kind": "Function"},
    ]), encoding="utf-8")
    cov = coverage(manifest, tmp_path)
    assert cov["total"] == 2 and cov["authored"] == 1
    assert cov["pending"] == ["clojure.core/filter"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_coverage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.enrich.coverage'`.

- [ ] **Step 3: Write `tools/enrich/coverage.py`**

```python
# tools/enrich/coverage.py
"""Reconcile the enrich manifest (work-list) against authored wiki pages."""
from __future__ import annotations
import json
from pathlib import Path

_CONTENT_DIRS = ("reference", "concepts", "projects", "entities")


def page_path_for(concept_id: str, kind: str) -> str:
    """Stdlib concept id (<ns>/<name>) → its reference page path (POSIX, repo-relative)."""
    return f"reference/{concept_id}.md"


def authored_ids(root: Path) -> set[str]:
    root = Path(root)
    ids: set[str] = set()
    for d in _CONTENT_DIRS:
        base = root / d
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            if md.name in ("index.md", "log.md"):
                continue
            rel = md.relative_to(base).with_suffix("")
            ids.add("/".join(rel.parts))
    return ids


def coverage(manifest_path: Path, root: Path) -> dict:
    records = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    have = authored_ids(Path(root))
    pending = [r["id"] for r in records if r["id"] not in have]
    return {"total": len(records), "authored": len(records) - len(pending),
            "pending": pending}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_coverage.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/enrich/coverage.py tools/tests/test_coverage.py
git commit -m "feat: enrich coverage — reconcile manifest ids against authored pages"
```

---

## Task 2: `enrich status` — coverage report CLI

**Files:**
- Create: `tools/enrich/status.py`
- Modify: `lgx.edn`, `Makefile`, `tools/tests/test_lgx_edn.py`
- Test: `tools/tests/test_enrich_status.py`

**Interfaces:**
- Consumes: `coverage()` (Task 1).
- Produces: `render_status(cov: dict, sample: int = 10) -> str` (human report) and CLI `python -m tools.enrich.status --manifest <path> [--root .]` → prints the report, exit 0. `lgx status` / `make status` run it against `.enrich/manifest.json`.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_enrich_status.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.status import render_status  # noqa: E402

def test_render_status_summarizes_counts():
    out = render_status({"total": 296, "authored": 5, "pending": ["clojure.core/filter"]})
    assert "5/296" in out
    assert "clojure.core/filter" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enrich_status.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `tools/enrich/status.py`**

```python
# tools/enrich/status.py
"""Report wiki authoring coverage against the enrich manifest."""
from __future__ import annotations
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.coverage import coverage  # noqa: E402


def render_status(cov: dict, sample: int = 10) -> str:
    lines = [f"coverage: {cov['authored']}/{cov['total']} concepts authored "
             f"({len(cov['pending'])} pending)"]
    if cov["pending"]:
        lines.append("next pending:")
        lines += [f"  - {pid}" for pid in cov["pending"][:sample]]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-status")
    p.add_argument("--manifest", type=Path, default=Path(".enrich/manifest.json"))
    p.add_argument("--root", type=Path, default=Path("."))
    args = p.parse_args(argv)
    if not args.manifest.exists():
        print(f"no manifest at {args.manifest}; run `lgx enrich` first", file=sys.stderr)
        return 1
    print(render_status(coverage(args.manifest, args.root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enrich_status.py -v`
Expected: PASS.

- [ ] **Step 5: Wire lgx + make; update lgx test**

Add to `lgx.edn` `:tasks`:
```clojure
         status {:doc "Report wiki authoring coverage vs the enrich manifest"
                 :do [{:sh "python -m tools.enrich.status"}]}
```
Add to `Makefile`:
```makefile
status: ## Report authoring coverage vs the enrich manifest
	python -m tools.enrich.status
```
Update `tools/tests/test_lgx_edn.py` to include `status` in the required-task lists (both the substring check and the lgx-validity check). Verify `mise exec -- lgx help` lists `status`, no "invalid lgx.edn".

- [ ] **Step 6: Full suite + commit**

Run: `cd ~/development/let-go-wiki && python -m pytest tools -q` → all pass.
```bash
git add tools/enrich/status.py tools/tests/test_enrich_status.py lgx.edn Makefile tools/tests/test_lgx_edn.py
git commit -m "feat: enrich status coverage report + lgx/make wiring"
```

---

## Task 3: `enrich next` — authoring brief generator

**Files:**
- Create: `tools/enrich/next_batch.py`
- Modify: `lgx.edn`, `Makefile`, `tools/tests/test_lgx_edn.py`
- Test: `tools/tests/test_next_batch.py`

**Interfaces:**
- Consumes: `coverage()` (Task 1); the manifest (Plan B); `_meta/taxonomy.md`.
- Produces: `next_briefs(manifest_path, root, count, out_dir) -> list[Path]` — picks the first `count` pending concepts, and for EACH writes `<out_dir>/<safe-id>.md` — an authoring brief containing: the concept record (id/kind/name/ns/signature/doc/source_path), the target page path (`page_path_for`), the list of SIBLING ids in the same ns (for cross-linking), and the allowed tag vocabulary (from taxonomy). CLI `python -m tools.enrich.next --count N [--out .enrich/briefs]`.
- The brief is what a Task-4 authoring subagent reads. A `safe-id` replaces `/` with `__`.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_next_batch.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.next_batch import next_briefs  # noqa: E402

def _manifest(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps([
        {"id":"clojure.core/map","kind":"Function","name":"map","ns":"clojure.core",
         "signature":"(map [f coll])","doc":"Apply f.","source_path":"core.lg"},
        {"id":"clojure.core/filter","kind":"Function","name":"filter","ns":"clojure.core",
         "signature":"(filter [pred coll])","doc":"Keep matching.","source_path":"core.lg"},
    ]), encoding="utf-8")
    return m

def test_next_writes_one_brief_per_pending(tmp_path):
    (tmp_path / "_meta").mkdir()
    (tmp_path / "_meta" / "taxonomy.md").write_text("- `stdlib`\n- `clojure`\n", encoding="utf-8")
    briefs = next_briefs(_manifest(tmp_path), tmp_path, count=2, out_dir=tmp_path/"briefs")
    assert len(briefs) == 2
    text = (tmp_path/"briefs"/"clojure.core__map.md").read_text(encoding="utf-8")
    assert "(map [f coll])" in text                       # signature
    assert "reference/clojure.core/map.md" in text        # target path
    assert "clojure.core/filter" in text                  # sibling id
    assert "stdlib" in text                                # taxonomy tag offered

def test_next_skips_already_authored(tmp_path):
    (tmp_path / "_meta").mkdir(); (tmp_path/"_meta"/"taxonomy.md").write_text("- `stdlib`\n", encoding="utf-8")
    (tmp_path / "reference" / "clojure.core").mkdir(parents=True)
    (tmp_path / "reference" / "clojure.core" / "map.md").write_text("x", encoding="utf-8")
    briefs = next_briefs(_manifest(tmp_path), tmp_path, count=5, out_dir=tmp_path/"briefs")
    names = {b.name for b in briefs}
    assert names == {"clojure.core__filter.md"}           # map already authored → skipped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_next_batch.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `tools/enrich/next_batch.py`**

```python
# tools/enrich/next_batch.py
"""Generate per-concept authoring briefs for the next batch of pending concepts."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.coverage import authored_ids, page_path_for  # noqa: E402

_TAG_RE = re.compile(r"^- `([a-z0-9-]+)`", re.MULTILINE)


def _tags(root: Path) -> list[str]:
    tax = root / "_meta" / "taxonomy.md"
    return _TAG_RE.findall(tax.read_text(encoding="utf-8")) if tax.exists() else []


def next_briefs(manifest_path: Path, root: Path, count: int, out_dir: Path) -> list[Path]:
    root, out_dir = Path(root), Path(out_dir)
    records = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    have = authored_ids(root)
    by_ns: dict[str, list[str]] = {}
    for r in records:
        by_ns.setdefault(r["ns"], []).append(r["id"])
    tags = _tags(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for r in records:
        if len(written) >= count:
            break
        if r["id"] in have:
            continue
        siblings = [i for i in by_ns.get(r["ns"], []) if i != r["id"]][:40]
        brief = out_dir / (r["id"].replace("/", "__") + ".md")
        brief.write_text(_render_brief(r, tags, siblings), encoding="utf-8")
        written.append(brief)
    return written


def _render_brief(r: dict, tags: list[str], siblings: list[str]) -> str:
    return (
        f"# Authoring brief: {r['id']}\n\n"
        f"- **Target page:** `{page_path_for(r['id'], r['kind'])}`\n"
        f"- **kind:** {r['kind']}\n- **ns:** {r['ns']}\n- **name:** {r['name']}\n"
        f"- **signature:** `{r['signature']}`\n"
        f"- **source_path:** {r['source_path']}\n\n"
        f"## Docstring (from source — ground the page in this, do not contradict)\n\n"
        f"{r.get('doc') or '(none)'}\n\n"
        f"## Allowed tags (choose ≤5 from _meta/taxonomy.md)\n\n"
        + ", ".join(tags) + "\n\n"
        f"## Sibling concept ids (same ns — link with file-relative `.md` links)\n\n"
        + "\n".join(f"- {s}" for s in siblings) + "\n\n"
        f"## Instructions\n\n"
        f"Follow `tools/enrich/prompts/reference_instruction.md`. Construct 1–3 example\n"
        f"forms, evaluate each with `lg -e '<form>'`, and use the REAL output (never\n"
        f"invented). Write the page at the target path; it must pass\n"
        f"`python tools/check_wiki.py .`. status: speculative.\n"
    )


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-next")
    p.add_argument("--manifest", type=Path, default=Path(".enrich/manifest.json"))
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--out", type=Path, default=Path(".enrich/briefs"))
    args = p.parse_args(argv)
    briefs = next_briefs(args.manifest, args.root, args.count, args.out)
    print(f"enrich next: wrote {len(briefs)} brief(s) -> {args.out}")
    for b in briefs:
        print(f"  {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_next_batch.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire lgx + make; update lgx test**

Add `next` task to `lgx.edn` (`:do [{:sh "python -m tools.enrich.next --count 5"}]`) and a `Makefile` `next` target (`python -m tools.enrich.next --count $(or $(COUNT),5)`). Update `test_lgx_edn.py` required-task lists to include `next`. Verify lgx lists it.

- [ ] **Step 6: Full suite + commit**

```bash
git add tools/enrich/next_batch.py tools/tests/test_next_batch.py lgx.edn Makefile tools/tests/test_lgx_edn.py
git commit -m "feat: enrich next — per-concept authoring brief generator + wiring"
```

---

## Task 4: Walking-skeleton stdlib population (agent-driven)

**Deliverable:** 5 real stdlib `reference/` pages authored via subagents, validated, reviewed, and published live. This proves the whole loop end-to-end. NOT TDD — the verification gate is the "test."

**Preconditions:** `lg` present; `../let-go` checked out. Run `python -m tools.enrich.prepare --source-root ../let-go` to (re)build `.enrich/manifest.json`.

- [ ] **Step 1: Generate the batch briefs**

Pick 5 high-value, present-in-manifest concepts (verify each is in the manifest first with `python -m tools.enrich.status`): `clojure.core/map`, `clojure.core/filter`, `clojure.core/reduce`? — NOTE `reduce` may be a Go-native absent from the manifest; if `enrich status` shows it pending-because-absent, substitute a manifest-present one (e.g. `clojure.core/apply`, `clojure.core/mapv`, `clojure.core/comp`, `clojure.core/partial`). Run:
```bash
cd ~/development/let-go-wiki
python -m tools.enrich.prepare --source-root ../let-go
python -m tools.enrich.next --count 5
```
Confirm 5 briefs exist under `.enrich/briefs/`.

- [ ] **Step 2: Author each page via a subagent (one per brief)**

For each brief, dispatch a Claude authoring subagent. Dispatch prompt skeleton (fill `<BRIEF_PATH>`):
> Author one let-go-wiki page. Read the brief `<BRIEF_PATH>` and the prompt `tools/enrich/prompts/reference_instruction.md`. You may run `lg -e '<form>'` (lg is on PATH) to get REAL example output — never invent it. Write the page at the brief's target path with the dual frontmatter (type from `kind`, category `concept`, tags ≤5 from the offered list, `resource` = the let-go source URL for `source_path`, `sources`, created/updated `2026-07-02`, `status: speculative`). Body: prose grounded in the docstring → `# Signature` → `# Examples` (real `lg -e` transcripts) → `# Citations` (the `resource` first; add clojuredocs.org/clojure.org links only if you are certain of them). Then run `python tools/check_wiki.py .` and fix any error it reports for your page. Report the page path and the check_wiki result.

- [ ] **Step 3: Validate the batch**

```bash
cd ~/development/let-go-wiki
python tools/check_wiki.py .            # expect: check_wiki: OK
python ~/pkm/.claude/skills/wiki/wiki-check-name.py reference/clojure.core/map.md || true  # name-collision guard (best-effort)
```
Every new page must pass `check_wiki`. Fix or re-dispatch any that don't.

- [ ] **Step 4: Accuracy review (subagent)**

Dispatch one reviewer subagent: "Review these N new `reference/` pages against the actual let-go source (`../let-go/pkg/rt/core/core.lg`) and real `lg -e` behavior. For each: is the description faithful to the docstring, is the signature correct, do the `# Examples` outputs match what `lg -e` actually prints? List any inaccuracies with the page + line." Fix flagged issues. Promote accurate pages from `status: speculative` → `status: stable` (edit frontmatter).

- [ ] **Step 5: Bookkeeping + publish + verify live**

```bash
cd ~/development/let-go-wiki
# Update index.md: add the 5 pages under a "Reference" section (one bullet each).
# Append a log.md entry: "## [2026-07-02] ingest | stdlib batch 1 (5 concepts)".
python tools/viz/render_viz.py . viz.html    # regenerate graph
python tools/build_site.py                    # must build --strict clean
python -m tools.enrich.status                 # coverage should show authored >= 5
git add reference/ index.md log.md viz.html
git commit -m "content: author stdlib batch 1 (map/filter/... ) — reviewed to stable"
git push origin main
```
Verify: after CI, `curl -s -o /dev/null -w '%{http_code}' https://nnunley.github.io/let-go-wiki/reference/clojure.core/map/` returns 200.

---

## Task 5: Internals worked example — `concepts/indexed-rpn-ir.md` (agent-driven)

**Deliverable:** the required Indexed-RPN IR internals page, with external references. This is the "developing let-go" authoring pattern (read Go source + design docs, not the manifest).

- [ ] **Step 1: Author the page via a subagent**

Dispatch an authoring subagent with this context:
> Author `concepts/indexed-rpn-ir.md` — a "developing let-go" internals concept page about let-go's intermediate representation. Read these sources in `~/development/let-go`: `pkg/ir/op_generated.go` (canonical header + Op catalogue), `pkg/ir/ir_ops.lg` (op definitions), and design docs under `docs/superpowers/{specs,plans}/` matching `*ir*`/`*sem-ir*`/`*lower*` (e.g. `2026-05-24-ir-cse-plan.md`). Frontmatter: `type: Concept`, `category: concept`, `title: "Indexed-RPN IR"`, tags ≤5 from taxonomy (e.g. `[compiler, bytecode, vm]`), `resource: "https://github.com/nooga/let-go/tree/main/pkg/ir/op_generated.go"`, `sources`, dates `2026-07-02`, `status: speculative`. Body — get the relationship EXACTLY right (do not conflate): **indexed-RPN is not SSA; it is an SSA-equivalent form.** Explain that the IR uses an **indexed-RPN (postfix) encoding** where a value's identity comes from its position/index (so you get SSA-like value numbering without explicit SSA names — Burak Emir's point), combined with a **block-parameter** control-flow structure (block args are the cross-block value channel, the SSA-style part). Ops pop operand-arity values off the RPN-walk stack and push 0 or 1; each op carries a "pure" flag governing CSE/fold/hoist; the op catalogue lives in `ir_ops.lg`, generated into `op_generated.go`. State plainly that indexed-RPN and SSA are *equivalent forms*, not the same thing. Cross-link `[stack vm](../concepts/stack-vm.md)` and `[let-go](../entities/let-go.md)` with file-relative links. **`# Citations` MUST include the external design references verbatim from the source header:** Burak Emir, "Indexed Reverse Polish Notation" (https://burakemir.ch — verify/curate the exact URL if reachable, else cite as named reference); Carbon Language semantic IR (`toolchain/sem_ir`); Swift SIL; Cranelift; MLIR (block-parameter SSA). Then run `python tools/check_wiki.py .` and fix any error for this page. Report the result.

- [ ] **Step 2: Validate + review**

```bash
cd ~/development/let-go-wiki && python tools/check_wiki.py .   # expect OK
```
Dispatch a reviewer subagent to check the page is faithful to `pkg/ir/op_generated.go`, that the external references are present and correctly attributed (Burak Emir / Carbon / SIL / Cranelift / MLIR), and — critically — that the page does **not** claim indexed-RPN *is* SSA: it must present indexed-RPN as an SSA-*equivalent* encoding, distinct from the block-parameter (SSA-style) structure. Fix inaccuracies; promote to `stable` when accurate.

- [ ] **Step 3: Bookkeeping + publish**

```bash
cd ~/development/let-go-wiki
# index.md: add concepts/indexed-rpn-ir under "Concepts"; log.md: append ingest entry.
python tools/viz/render_viz.py . viz.html
python tools/build_site.py                       # --strict clean
git add concepts/indexed-rpn-ir.md index.md log.md viz.html
git commit -m "content: document the indexed-RPN block-parameter SSA IR (external refs cited)"
git push origin main
```

---

## Task 6: First project case study — `projects/xsofy.md` (agent-driven)

**Deliverable:** the first "using let-go in anger" project page, authored by reading the repo.

- [ ] **Step 1: Author via a subagent**

Dispatch an authoring subagent:
> Author `projects/xsofy.md`. Read `~/development/xsofy` (README.md, main.lg, structure). Frontmatter: `type: Project`, `category: project`, `title: "Xs of Y (xsofy)"`, tags ≤5 (e.g. `[roguelike, wasm, lisp]`), `resource: "https://github.com/nooga/xsofy"`, `sources`, dates `2026-07-02`, `status: speculative`. Body: what xsofy is (a browser+terminal roguelike written in let-go; the magic system is Lisp — runes are s-expressions), how it exercises let-go (persistent data structures, WASM build, no deps, ~6ms startup), and 1–2 concrete idioms worth noting for "using let-go". Cross-link `[let-go](../entities/let-go.md)`. `# Citations`: the repo + the play link. Run `python tools/check_wiki.py .` and fix errors. Report.

- [ ] **Step 2: Validate + review + publish**

```bash
cd ~/development/let-go-wiki && python tools/check_wiki.py .   # OK
```
Reviewer subagent checks faithfulness to the xsofy repo; fix; promote to stable. Then:
```bash
# index.md: add projects/xsofy under "Projects"; log.md: append. Regenerate viz + build.
python tools/viz/render_viz.py . viz.html && python tools/build_site.py
git add projects/xsofy.md index.md log.md viz.html
git commit -m "content: xsofy project case study" && git push origin main
```

---

## Task 7: Sprint runbook + coverage checkpoint

**Files:**
- Create: `docs/superpowers/runbooks/population-sprint.md`
- Modify: `AGENTS.md` (add a short "Running a population sprint" pointer)

**Deliverable:** a repeatable procedure so the loop can be re-run to full coverage, plus a coverage checkpoint.

- [ ] **Step 1: Write the runbook**

Create `docs/superpowers/runbooks/population-sprint.md` documenting the repeatable loop (the sequence proven in Tasks 4–6), verbatim commands:
```markdown
# Population sprint runbook
1. `python -m tools.enrich.prepare --source-root ../let-go`   # refresh manifest
2. `python -m tools.enrich.status`                            # see coverage/pending
3. `python -m tools.enrich.next --count N`                    # write N briefs
4. Dispatch one authoring subagent per brief (reference_instruction.md; real `lg -e`).
5. `python tools/check_wiki.py .`                             # gate: must be OK
6. Dispatch a reviewer subagent; fix; promote speculative→stable.
7. Update index.md + log.md; `python tools/viz/render_viz.py . viz.html`; `python tools/build_site.py`.
8. `git add … && git commit && git push`; verify the live page returns 200.
Scope beyond stdlib: projects (xsofy/lgcr/lgx/legmacs/let-go-lab) author one page per repo;
internals (concepts/) read Go packages + docs/superpowers; docs-crawl pass uses
web_ingestion_instruction.md (four-gate references, clojure-compat/interop/limitations).
```

- [ ] **Step 2: Point AGENTS.md at it**

Add to `AGENTS.md` a line under build/publish: `- Populate: see docs/superpowers/runbooks/population-sprint.md (run via lgx status / lgx next).`

- [ ] **Step 3: Coverage checkpoint + commit**

```bash
cd ~/development/let-go-wiki
python -m tools.enrich.status            # record authored/total in the commit message
python -m pytest tools -q                # all pass
git add docs/superpowers/runbooks/population-sprint.md AGENTS.md
git commit -m "docs: population sprint runbook + AGENTS pointer"
git push origin main
```

---

## Self-Review

**Spec coverage:** the authoring loop consuming the Plan B manifest (§7 "Claude subagent per concept") → Tasks 3–4; the reference prompt's real-`lg -e`/frontmatter/relative-link contract (§7, §3) enforced by briefs + check_wiki gate → Tasks 3–4; project case studies (§5) → Task 6 (xsofy; runbook extends to lgcr/lgx/legmacs/let-go-lab); internals "developing let-go" (§4 concepts/) → Task 5; the **user requirement** (document indexed-RPN + external references) → Task 5 + Global Constraints; publish to the styled site (§8) → Tasks 4–6 build/push; taxonomy/coordination the Plan B review flagged → briefs carry taxonomy + siblings (Task 3). Deferred: full stdlib coverage (runbook re-run), the web/docs-crawl pass (runbook note), Go-internals enumeration tooling (Plan B deferred).

**Placeholder scan:** none in the TDD tasks (Tasks 1–3 have complete code). Tasks 4–6 are agent-driven; their "verification" is concrete runnable gates (`check_wiki`, `build_site --strict`, live 200, `enrich status`), not placeholders. The one runtime substitution (a chosen concept turning out to be a Go-native absent from the manifest) is handled explicitly in Task 4 Step 1 with named alternates.

**Type consistency:** `page_path_for(id, kind)`, `authored_ids(root)`, `coverage(manifest, root)` (Task 1) are used unchanged by `render_status`/`coverage` (Task 2) and `next_briefs` (Task 3); brief filename convention (`<id with / → __>.md`) is consistent between `next_briefs` and its test; manifest record keys match Plan B's `prepare` output.

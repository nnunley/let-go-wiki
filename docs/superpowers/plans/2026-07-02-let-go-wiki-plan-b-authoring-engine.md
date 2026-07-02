# let-go-wiki — Plan B: Authoring Engine (enrich, recast)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic authoring engine that feeds `enrich` — a let-go source reader, a `LetGoSource` that enumerates concepts + evaluates real examples, the two adapted enrich prompts, and a `prepare` step that emits a per-concept work manifest — so a later agent loop (Plan C) can author OKF pages.

**Architecture:** Because let-go's runtime reflection is thin (`ns-publics`/`doc`/`meta (var …)` are absent, verified 2026-07-02), stdlib concepts are enumerated by **reading `.lg` source through let-go's own reader** (`read-string`), which dogfoods let-go. `LetGoSource` (Python) drives that reader, extracts name/arglists/docstring, and evaluates example forms via `lg -e`. `enrich prepare` writes a manifest of concepts + evaluated examples; the LLM authoring that consumes it (dispatching Claude subagents per concept) is Plan C — Python cannot spawn Claude subagents, so this plan builds the deterministic, testable substrate and the prompts they use.

**Tech Stack:** Python 3.13 + pytest, the `lg` binary (on PATH; also via mise), let-go (`.lg`) for the reader script, EDN/JSON for the manifest.

## Global Constraints

- Python **3.13**; deps pinned in `requirements.txt`; run tests from repo root (`python -m pytest tools -q`).
- The `lg` binary is the eval/read backend: `lg -e '<form>'` evaluates and prints; it is on PATH (`/opt/homebrew/bin/lg`) and available via `mise exec -- lg`. Tests that need `lg` **skip** when it is unavailable (CI), never error.
- **Runtime introspection is thin** — do NOT rely on `ns-publics`, `ns-map`, `ns-interns`, `doc`, or `(meta (var f))`; they are absent/return nil. Enumerate stdlib concepts by reading `.lg` source via the reader.
- Verified reader idiom: `(read-string (str "[" (slurp PATH) "]"))` returns a vector of all top-level forms. For a `defn`/`defmacro` form `f`: `(first f)`=op symbol, `(second f)`=name symbol; a docstring (when present) is the first string after the name; arglist(s) are the vector(s) after the optional docstring/attr-map.
- OKF/llm_wiki page contract (from the design spec) is unchanged: dual frontmatter (`type`+`category`+…), file-relative `.md` links, `# Signature`/`# Examples`/`# Citations` body sections, `status: speculative` for drafts.
- Reuse existing tooling; do not duplicate. `tools/check_wiki.py` validates any page this engine's consumers produce.
- v1 scope: the **let-go stdlib** (namespaces defined in `.lg` source, primarily `pkg/rt/core/core.lg`). Enumerating Go-internal packages (`pkg/vm`, `pkg/compiler`) for "developing let-go" concepts is **out of scope for Plan B** (deferred; noted in §Deferred).

---

## File Structure (created by this plan)

- `tools/letgo/enumerate.lg` — let-go reader script: reads a `.lg` file, prints one EDN map per top-level `def*` form.
- `tools/letgo/__init__.py`, `tools/letgo_source.py` — `LetGoSource`: enumerate concepts, read concept detail, eval examples.
- `tools/enrich/__init__.py`, `tools/enrich/prepare.py` — build the per-concept work manifest.
- `tools/enrich/prompts/reference_instruction.md` — structured-pass authoring prompt (recast for let-go).
- `tools/enrich/prompts/web_ingestion_instruction.md` — crawl-pass prompt (four gates + let-go extractions).
- `tools/enrich/config.toml` — which source files/namespaces to enumerate.
- `tools/tests/test_*.py` — one per component.
- `lgx.edn`, `Makefile` — add an `enrich` task/target.

---

## Task 1: let-go source reader — `tools/letgo/enumerate.lg`

**Files:**
- Create: `tools/letgo/enumerate.lg`, `tools/letgo/__init__.py`
- Test: `tools/tests/test_enumerate_lg.py`, fixture `tools/tests/fixtures/sample.lg`

**Interfaces:**
- Produces: running `lg tools/letgo/enumerate.lg <file.lg>` prints, one per line, an EDN map per top-level def form: `{:op "defn" :name "square" :doc "Return n squared." :arglists [[n]] :line 1}`. Consumed by `LetGoSource.list_concepts`/`read_concept` (Task 2/3).

- [ ] **Step 1: Create the test fixture**

Create `tools/tests/fixtures/sample.lg`:
```clojure
(defn square
  "Return n squared."
  [n]
  (* n n))

(defn add
  ([a] a)
  ([a b] (+ a b)))

(def answer 42)

(defmacro unless [test body]
  (list 'if test nil body))

(defn- helper [x] x)
```

- [ ] **Step 2: Write the failing test**

```python
# tools/tests/test_enumerate_lg.py
import json, shutil, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tools/tests/fixtures/sample.lg"

def _lg():
    if shutil.which("lg"):
        return ["lg"]
    if shutil.which("mise"):
        try:
            if subprocess.run(["mise","exec","--","lg","-e","nil"], cwd=ROOT,
                              capture_output=True, timeout=60).returncode == 0:
                return ["mise","exec","--","lg"]
        except (OSError, subprocess.SubprocessError):
            return None
    return None

def _run_enumerate():
    lg = _lg()
    if lg is None:
        pytest.skip("lg not available")
    script = ROOT / "tools/letgo/enumerate.lg"
    r = subprocess.run(lg + [str(script), str(FIX)], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    import re
    # enumerate.lg prints one EDN map per line; convert EDN-ish to python via a
    # tolerant parse: names/ops are strings, arglists are lists. The script emits
    # JSON (not EDN) to keep the Python side dependency-free — see Step 3.
    return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]

def test_enumerates_all_def_forms():
    forms = _run_enumerate()
    by_name = {f["name"]: f for f in forms}
    assert set(by_name) == {"square", "add", "answer", "unless", "helper"}

def test_defn_doc_and_arglist():
    f = next(f for f in _run_enumerate() if f["name"] == "square")
    assert f["op"] == "defn"
    assert f["doc"] == "Return n squared."
    assert f["arglists"] == [["n"]]

def test_multi_arity_arglists():
    f = next(f for f in _run_enumerate() if f["name"] == "add")
    assert f["arglists"] == [["a"], ["a", "b"]]
    assert f["doc"] is None

def test_def_and_macro_and_private():
    by = {f["name"]: f for f in _run_enumerate()}
    assert by["answer"]["op"] == "def"
    assert by["unless"]["op"] == "defmacro"
    assert by["helper"]["op"] == "defn-"
    assert by["helper"]["private"] is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enumerate_lg.py -v`
Expected: FAIL — `enumerate.lg` does not exist (subprocess returncode != 0), or SKIP if `lg` is unavailable (install lg first: `brew install nooga/tap/let-go` or via mise).

- [ ] **Step 4: Write `tools/letgo/enumerate.lg`**

The script reads the file path from the command line, reads all top-level forms, and prints one JSON object per def form. Emit JSON (not EDN) so the Python side needs no EDN parser. Symbols are printed with `name`/`str`.

```clojure
;; enumerate.lg — read a .lg file's top-level def forms, print one JSON object
;; per form: {"op","name","doc","arglists","private","line"}.
;; Usage: lg enumerate.lg <path-to-file.lg>
(def def-ops #{'def 'defn 'defn- 'defmacro 'definline})

(defn- json-str [s]
  ;; minimal JSON string escaping for the fields we emit
  (str "\"" (-> (str s)
                (clojure.string/replace "\\" "\\\\")
                (clojure.string/replace "\"" "\\\""))
       "\""))

(defn- json-arglists [arglists]
  (str "[" (clojure.string/join ","
             (map (fn [al]
                    (str "[" (clojure.string/join "," (map json-str al)) "]"))
                  arglists))
       "]"))

(defn- private? [op form]
  (or (= op 'defn-)
      (boolean (:private (meta (second form))))))

(defn- extract-arglists [op form]
  ;; forms after the name, skipping an optional docstring and attr-map.
  (let [after (drop 2 form)
        after (if (string? (first after)) (rest after) after)
        after (if (map? (first after)) (rest after) after)]
    (cond
      (vector? (first after)) [(first after)]          ; single arity
      (list? (first after))   (map first after)         ; multi-arity: ([args] body)...
      :else [])))

(defn- doc-of [form]
  (let [x (nth form 2 nil)]
    (when (string? x) x)))

(defn- emit [form]
  (let [op (first form)]
    (when (contains? def-ops op)
      (let [nm (second form)
            arglists (if (= op 'def) [] (extract-arglists op form))
            doc (doc-of form)]
        (println
          (str "{"
               "\"op\":" (json-str op) ","
               "\"name\":" (json-str nm) ","
               "\"doc\":" (if doc (json-str doc) "null") ","
               "\"arglists\":" (json-arglists arglists) ","
               "\"private\":" (if (private? op form) "true" "false")
               "}"))))))

(let [path (first *command-line-args*)
      forms (read-string (str "[" (slurp path) "]"))]
  (doseq [f forms]
    (when (and (seq? f) (symbol? (first f)))
      (emit f))))
```

Notes for the implementer:
- Confirm the CLI-args accessor: this script assumes `*command-line-args*`. If `lg` exposes args differently, adapt (check `lg -e '(println *command-line-args*)' foo bar`). If args are unavailable when running a script file, fall back to reading the path from stdin and invoke as `lg enumerate.lg` with the path piped — but prefer the args form; verify first.
- `line` is omitted above (the reader idiom loses line numbers). If line numbers are needed, they are best-effort; the test does not assert `line`, so leaving it out is fine. Do not add a `line` key the test doesn't check.
- `clojure.string/join`/`replace` must be available; if the namespace alias differs in let-go, require/adjust. Verify with a quick `lg -e '(clojure.string/join "," ["a" "b"])'`.

- [ ] **Step 5: Iterate against the fixture until tests pass**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enumerate_lg.py -v`
Expected: PASS (4 tests). If `lg`'s reader chokes on the whole-file `[...]` wrap for real core.lg later, that is handled in Task 2 (per-file error handling); Task 1 only needs the fixture green.

- [ ] **Step 6: Commit**

```bash
git add tools/letgo/enumerate.lg tools/letgo/__init__.py tools/tests/test_enumerate_lg.py tools/tests/fixtures/sample.lg
git commit -m "feat: let-go source reader (enumerate.lg) — dogfooded .lg form extraction"
```

---

## Task 2: `LetGoSource.list_concepts` — `tools/letgo_source.py`

**Files:**
- Create: `tools/letgo_source.py`
- Test: `tools/tests/test_letgo_source_list.py` (reuses `tools/tests/fixtures/sample.lg`)

**Interfaces:**
- Consumes: `tools/letgo/enumerate.lg` (Task 1).
- Produces:
  - `@dataclass Concept: id: str; kind: str; name: str; ns: str; arglists: list[list[str]]; doc: str | None; private: bool; source_path: str`
  - `class LetGoSource(lg_cmd: list[str] | None = None)` with `list_concepts(source_file: Path, ns: str) -> list[Concept]`.
  - `kind` is the OKF type derived from op: `defn`/`defn-`/`definline`→`"Function"`, `defmacro`→`"Macro"`, `def`→`"Var"`. `id` = `f"{ns}/{name}"`.
  - Module-level `resolve_lg() -> list[str] | None` (returns the argv prefix for `lg`, or None) — reused by tests and Task 3.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_letgo_source_list.py
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
    assert set(cs) == {"square", "add", "answer", "unless", "helper"}
    assert cs["square"].arglists == [["n"]]
    assert cs["add"].arglists == [["a"], ["a", "b"]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_letgo_source_list.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'letgo_source'`.

- [ ] **Step 3: Write `tools/letgo_source.py` (list part)**

```python
# tools/letgo_source.py
"""Enumerate let-go stdlib concepts by reading .lg source via let-go's reader,
and evaluate example forms via `lg -e`. Runtime var introspection is thin, so
this reads source rather than reflecting."""
from __future__ import annotations
import json, shutil, subprocess
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ENUMERATE = _ROOT / "letgo" / "enumerate.lg"
_KIND = {"defn": "Function", "defn-": "Function", "definline": "Function",
         "defmacro": "Macro", "def": "Var"}


def resolve_lg() -> list[str] | None:
    """argv prefix that runs the `lg` binary, or None if unavailable."""
    if shutil.which("lg"):
        return ["lg"]
    if shutil.which("mise"):
        try:
            r = subprocess.run(["mise", "exec", "--", "lg", "-e", "nil"],
                               capture_output=True, timeout=60)
            if r.returncode == 0:
                return ["mise", "exec", "--", "lg"]
        except (OSError, subprocess.SubprocessError):
            return None
    return None


@dataclass
class Concept:
    id: str
    kind: str
    name: str
    ns: str
    arglists: list[list[str]] = field(default_factory=list)
    doc: str | None = None
    private: bool = False
    source_path: str = ""


class LetGoSourceError(RuntimeError):
    pass


class LetGoSource:
    def __init__(self, lg_cmd: list[str] | None = None):
        self.lg = lg_cmd or resolve_lg()
        if self.lg is None:
            raise LetGoSourceError("lg binary not available")

    def _enumerate(self, source_file: Path) -> list[dict]:
        r = subprocess.run(self.lg + [str(_ENUMERATE), str(source_file)],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise LetGoSourceError(f"enumerate.lg failed for {source_file}: {r.stderr}")
        out = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                out.append(json.loads(line))
        return out

    def list_concepts(self, source_file: Path, ns: str) -> list[Concept]:
        concepts = []
        for f in self._enumerate(Path(source_file)):
            kind = _KIND.get(f["op"], "Var")
            concepts.append(Concept(
                id=f"{ns}/{f['name']}",
                kind=kind, name=f["name"], ns=ns,
                arglists=f.get("arglists") or [],
                doc=f.get("doc"),
                private=bool(f.get("private")),
                source_path=str(source_file),
            ))
        return concepts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_letgo_source_list.py -v`
Expected: PASS (2 tests; or SKIP if lg unavailable).

- [ ] **Step 5: Commit**

```bash
git add tools/letgo_source.py tools/tests/test_letgo_source_list.py
git commit -m "feat: LetGoSource.list_concepts via the .lg reader"
```

---

## Task 3: `read_concept` + `eval_example` (sandboxed `lg -e`)

**Files:**
- Modify: `tools/letgo_source.py`
- Test: `tools/tests/test_letgo_source_eval.py`

**Interfaces:**
- Consumes: `LetGoSource` (Task 2), `resolve_lg`.
- Produces:
  - `LetGoSource.read_concept(concept: Concept) -> dict` → `{"id","kind","name","ns","arglists","doc","signature","source_path"}` where `signature` is a human string like `(square [n])` or multi-arity `(add [a] [a b])`.
  - `LetGoSource.eval_example(form: str, timeout: float = 5.0) -> dict` → `{"form","output","error"}`; runs `lg -e form`; on timeout/error, `output=""` and `error` is a short message (never raises). stdout is stripped.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_letgo_source_eval.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_letgo_source_eval.py -v`
Expected: FAIL — `AttributeError: 'LetGoSource' object has no attribute 'read_concept'`.

- [ ] **Step 3: Add the methods to `tools/letgo_source.py`**

```python
    def read_concept(self, concept: Concept) -> dict:
        if concept.arglists:
            arities = " ".join("[" + " ".join(a) + "]" for a in concept.arglists)
            signature = f"({concept.name} {arities})"
        else:
            signature = f"{concept.name}"
        return {
            "id": concept.id, "kind": concept.kind, "name": concept.name,
            "ns": concept.ns, "arglists": concept.arglists, "doc": concept.doc,
            "signature": signature, "source_path": concept.source_path,
        }

    def eval_example(self, form: str, timeout: float = 5.0) -> dict:
        try:
            r = subprocess.run(self.lg + ["-e", form], capture_output=True,
                               text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"form": form, "output": "", "error": "timeout"}
        except (OSError, subprocess.SubprocessError) as e:
            return {"form": form, "output": "", "error": str(e)}
        if r.returncode != 0:
            err = (r.stderr or r.stdout).strip().splitlines()
            return {"form": form, "output": "", "error": err[0] if err else "error"}
        return {"form": form, "output": r.stdout.strip(), "error": None}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_letgo_source_eval.py -v`
Expected: PASS (3 tests; or SKIP if lg unavailable).

- [ ] **Step 5: Commit**

```bash
git add tools/letgo_source.py tools/tests/test_letgo_source_eval.py
git commit -m "feat: LetGoSource.read_concept + sandboxed eval_example (lg -e)"
```

---

## Task 4: `enrich prepare` — per-concept work manifest

**Files:**
- Create: `tools/enrich/__init__.py`, `tools/enrich/prepare.py`, `tools/enrich/config.toml`
- Modify: `lgx.edn`, `Makefile`
- Test: `tools/tests/test_enrich_prepare.py`

**Interfaces:**
- Consumes: `LetGoSource` (Tasks 2–3).
- Produces:
  - `prepare(config_path: Path, out_dir: Path, source_root: Path, lg=None) -> Path` — reads `config.toml` (a list of `[[source]] file="..." ns="..."`), enumerates each, and writes `out_dir/manifest.json`: a list of records `{"id","kind","name","ns","signature","doc","source_path","status":"pending"}`. Returns the manifest path.
  - CLI `python -m tools.enrich.prepare --source-root <path-to-let-go> [--out <dir>]`.
  - `lgx enrich` / `make enrich` run the CLI with defaults.
- The manifest is what a Plan C agent loop consumes (one authoring subagent per `pending` record). This task does NOT author pages.

- [ ] **Step 1: Write `tools/enrich/config.toml`**

```toml
# Source files to enumerate for the let-go stdlib. Paths are relative to
# --source-root (the let-go checkout). Add more as coverage grows.
[[source]]
file = "pkg/rt/core/core.lg"
ns = "clojure.core"
```

- [ ] **Step 2: Write the failing test**

```python
# tools/tests/test_enrich_prepare.py
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.prepare import prepare  # noqa: E402
from tools.letgo_source import resolve_lg  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

def test_prepare_writes_manifest_from_config(tmp_path):
    if resolve_lg() is None:
        pytest.skip("lg not available")
    # Point a temp config at the committed fixture, with source-root = repo root.
    cfg = tmp_path / "config.toml"
    cfg.write_text('[[source]]\nfile = "tools/tests/fixtures/sample.lg"\nns = "sample.core"\n',
                   encoding="utf-8")
    manifest = prepare(cfg, tmp_path / "work", ROOT)
    records = json.loads(Path(manifest).read_text(encoding="utf-8"))
    by = {r["name"]: r for r in records}
    assert by["square"]["signature"] == "(square [n])"
    assert by["square"]["kind"] == "Function"
    assert all(r["status"] == "pending" for r in records)
    assert by["square"]["doc"] == "Return n squared."
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enrich_prepare.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.enrich.prepare'`.

- [ ] **Step 4: Write `tools/enrich/prepare.py`**

```python
# tools/enrich/prepare.py
"""Build the per-concept work manifest that the Plan C authoring loop consumes."""
from __future__ import annotations
import argparse, json, sys, tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from letgo_source import LetGoSource  # noqa: E402


def prepare(config_path: Path, out_dir: Path, source_root: Path, lg=None) -> Path:
    config_path, out_dir, source_root = map(Path, (config_path, out_dir, source_root))
    cfg = tomllib.loads(config_path.read_text(encoding="utf-8"))
    src = LetGoSource(lg_cmd=lg)
    records: list[dict] = []
    for entry in cfg.get("source", []):
        source_file = source_root / entry["file"]
        for c in src.list_concepts(source_file, ns=entry["ns"]):
            detail = src.read_concept(c)
            records.append({
                "id": detail["id"], "kind": detail["kind"], "name": detail["name"],
                "ns": detail["ns"], "signature": detail["signature"],
                "doc": detail["doc"], "source_path": str(source_file),
                "status": "pending",
            })
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-prepare")
    p.add_argument("--source-root", required=True, type=Path,
                   help="Path to the let-go checkout")
    p.add_argument("--config", type=Path,
                   default=Path(__file__).resolve().parent / "config.toml")
    p.add_argument("--out", type=Path, default=Path(".enrich"))
    args = p.parse_args(argv)
    manifest = prepare(args.config, args.out, args.source_root)
    records = json.loads(manifest.read_text(encoding="utf-8"))
    print(f"enrich: {len(records)} concepts -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enrich_prepare.py -v`
Expected: PASS (or SKIP if lg unavailable).

- [ ] **Step 6: Wire `lgx.edn` + `Makefile`**

Add to `lgx.edn` `:tasks` map (symbol key, `:do`/`:sh` per the validated schema):
```clojure
         enrich {:doc "Prepare the per-concept authoring manifest from a let-go checkout"
                 :do [{:sh "python -m tools.enrich.prepare --source-root ../let-go"}]}
```
Add to `Makefile` (a target; `.enrich/` is generated — see Step 7):
```makefile
enrich: ## Prepare the authoring manifest (SOURCE_ROOT defaults to ../let-go)
	python -m tools.enrich.prepare --source-root $(or $(SOURCE_ROOT),../let-go)
```
Verify `lgx.edn` still validates: `mise exec -- lgx help` lists `enrich` and prints no "invalid lgx.edn". Update `tools/tests/test_lgx_edn.py` to include `enrich` in the required-task list.

- [ ] **Step 7: Gitignore the generated manifest dir**

Add `.enrich/` to `.gitignore` (generated work dir, not committed).

- [ ] **Step 8: Run full suite + commit**

Run: `cd ~/development/let-go-wiki && python -m pytest tools -q`
Expected: all pass (lg-dependent tests may skip).
```bash
git add tools/enrich lgx.edn Makefile .gitignore tools/tests/test_enrich_prepare.py tools/tests/test_lgx_edn.py
git commit -m "feat: enrich prepare — per-concept authoring manifest + lgx/make wiring"
```

---

## Task 5: Adapt the enrich prompts (SQL→Clojure) + invariants test

**Files:**
- Create: `tools/enrich/prompts/reference_instruction.md`, `tools/enrich/prompts/web_ingestion_instruction.md`
- Test: `tools/tests/test_enrich_prompts.py`

**Interfaces:**
- Produces: the two authoring prompts the Plan C subagents use. Source material to adapt is the vendored originals at
  `/private/tmp/claude-501/-Users-ndn-development-let-go-wiki/d4bf016b-09dd-44ce-b4c4-496559b95922/scratchpad/kc/okf/src/reference_agent/prompts/{reference_instruction.md,web_ingestion_instruction.md}` (read them; if that scratch path is gone, the equivalent content is summarized in the design spec §7). Rewrite them for let-go, preserving the transferable discipline.

- [ ] **Step 1: Write the failing invariants test**

The prompts are prose, but they must retain the load-bearing rules. Assert their presence so an edit can't silently drop them.

```python
# tools/tests/test_enrich_prompts.py
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "enrich" / "prompts"

def _read(name): return (P / name).read_text(encoding="utf-8").lower()

def test_reference_prompt_has_letgo_contract():
    t = _read("reference_instruction.md")
    for needle in ["# signature", "# examples", "# citations",
                   "file-relative", "status: speculative", "lg -e"]:
        assert needle in t, f"reference prompt missing: {needle}"
    # Must NOT carry over BigQuery/SQL specifics.
    for banned in ["bigquery", "sql", "# schema"]:
        assert banned not in t, f"reference prompt still mentions: {banned}"

def test_web_prompt_keeps_four_gates_and_letgo_extractions():
    t = _read("web_ingestion_instruction.md")
    for needle in ["four gate", "references/", "skip",
                   "clojure-compat", "interop", "limitation"]:
        assert needle in t, f"web prompt missing: {needle}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enrich_prompts.py -v`
Expected: FAIL — prompt files do not exist.

- [ ] **Step 3: Write `reference_instruction.md`**

```markdown
You are an enrichment agent that writes one **OKF/llm_wiki** page for a single
let-go stdlib concept, then stops. Your output is the page file content only.

## Workflow
1. You are given a concept record: id, kind (Function/Macro/Var), name, ns,
   signature, and docstring (from the .lg source), plus the list of sibling
   concept ids for cross-linking.
2. If example output would help, request evaluation of a small form; the
   harness runs `lg -e '<form>'` and returns the real output. Use ONLY real
   output — never invent REPL results.
3. Write the page and stop.

## Frontmatter (dual vocabulary, all keys required)
type: <kind>            # Function | Macro | Var
category: concept
title: "<name>"
description: "<one sentence; used verbatim in index.md>"
tags: [<from _meta/taxonomy.md, max 5>]
resource: "<source repo URL + path>"
sources: ["repo: nooga/let-go <path>, <date>"]
created/updated: "<date>"
status: speculative

## Body sections, in order
1. One–three sentences: what the concept is and when you use it (ground it in
   the docstring; do not contradict it).
2. `# Signature` — the signature string in a fenced `clojure` block.
3. `# Examples` — 1–3 fenced `clojure` blocks, each a real form and its actual
   `lg -e` output as a comment (`;; => ...`). No invented output.
4. `# Citations` — the concept's `resource` first, then any real sources.

## Cross-linking
Link related concepts with **file-relative** markdown links
(`[map](map.md)`, `[reduce](../concepts/reduce.md)`), never `/absolute`.
Only link ids that exist in the sibling list. One link per mention per section.

## Style
Concrete, no preamble/apology/narration. The body must be valid markdown ready
for direct consumption and must pass `tools/check_wiki.py`.
```

- [ ] **Step 4: Write `web_ingestion_instruction.md`**

```markdown
You augment an existing let-go OKF bundle from web pages, driving your own
crawl from seed URLs under hard guardrails (max-pages, allowed-hosts,
path-prefixes, denied-substrings, max-depth — enforced by the fetch tool; you
cannot exceed them).

## Per page, decide one of:
- **Enrich** an existing concept page: strict augmentation — keep every existing
  `#` heading and its content; add within/after. Never rewrite wholesale.
- **Mint** a `references/<slug>.md` doc — ONLY if it passes all **four gates**:
  1. referenceable-by-name from a concept page,
  2. not bundle-level meta (skip overview/intro/getting-started/tutorial/
     changelog/roadmap/faq),
  3. citation test (you can write "See the [X reference](...)" with a concrete
     noun),
  4. reuse test (≥2 concepts benefit, or one needs it as load-bearing).
  When in doubt, **skip**.

## let-go must-capture extractions (bypass the four gates)
These are inherently concept-shaped and reusable:
- **Clojure-compat notes** — where let-go diverges from Clojure JVM →
  `references/clojure-compat/<slug>.md`, cited from affected concept pages.
- **Interop rules** — Go ↔ let-go calling conventions → `references/interop/<slug>.md`.
- **Known limitations / edge cases** — from the README "Known limitations" and
  failing test-suite cases → `references/limitations/<slug>.md`.

## Rules
Cite only URLs you actually fetched. File-relative links only. Reference docs
use `type: Reference`, `category: reference`, `resource` = the page URL, tags
from `_meta/taxonomy.md`, `status: speculative`. Bodies must pass
`tools/check_wiki.py`. End with a one-line summary (pages fetched, docs updated,
references minted).
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/development/let-go-wiki && python -m pytest tools/tests/test_enrich_prompts.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Full suite + commit**

Run: `cd ~/development/let-go-wiki && python -m pytest tools -q` → all pass.
```bash
git add tools/enrich/prompts tools/tests/test_enrich_prompts.py
git commit -m "feat: let-go enrich prompts (reference + web) recast from OKF originals"
```

---

## Deferred (out of Plan B scope)

- **Go-internals enumeration** (`pkg/vm`, `pkg/compiler` → "developing let-go" concept pages). Needs a Go-doc reader (`go doc`/`go/doc`), a separate `Source`-like adapter. Plan a follow-on if desired.
- **Namespace pages** from `all-ns` (the runtime list is mostly internal IR/gogen namespaces; curate rather than auto-emit).
- **The authoring loop itself** (dispatching a Claude subagent per manifest record with `reference_instruction.md`) is **Plan C** — Python cannot spawn Claude subagents; the harness does.

## Self-Review

**Spec coverage (§7 authoring engine):** `LetGoSource` enumeration via the .lg reader (§7 note) → Tasks 1–2; `read_concept`/example eval via `lg -e` (§7 sampling) → Task 3; the two prompts with four-gate + augmentation + let-go extractions (§7 pass-2) → Task 5; `enrich` fronted by lgx/make (§6) → Task 4; manifest as the substrate for the Plan C subagent loop (§7 "Claude subagent per concept") → Task 4 + Deferred note. Frontmatter/relative-link/`# Signature`/`# Examples` contract (§3) → Task 5 prompt + invariants test.

**Placeholder scan:** none — every code step is complete. The two "verify the accessor" notes in Task 1 (Step 4) are explicit implementer verifications with a concrete fallback, not deferred work.

**Type consistency:** `Concept` dataclass fields (id/kind/name/ns/arglists/doc/private/source_path) are consistent across Tasks 2–4; `resolve_lg()`/`LetGoSource(lg_cmd=)` used consistently in Tasks 2–4 tests; `read_concept` returns `signature` used by Task 4 manifest; manifest record keys (id/kind/name/ns/signature/doc/source_path/status) consistent between `prepare` and its test.

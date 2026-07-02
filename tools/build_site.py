"""Stage content dirs into a MkDocs docs_dir and build the styled site."""
from __future__ import annotations
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml

CONTENT_DIRS = ("concepts", "entities", "ideas", "projects", "sources", "references")
_TITLE_CAT = {"concepts": "Concepts", "entities": "Entities", "ideas": "Ideas",
              "projects": "Projects", "sources": "Sources", "references": "References"}
# The OKF graph is a standalone HTML file (site/viz.html), not a MkDocs page, so
# it is linked as an external nav entry rather than rendered inside the theme.
GRAPH_URL = "https://nnunley.github.io/let-go-wiki/viz.html"

def _stage(root: Path, docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    # Copy index.md if it exists (optional for test/viz compatibility).
    index_src = root / "index.md"
    if index_src.exists():
        shutil.copy2(index_src, docs_dir / "index.md")
    for d in CONTENT_DIRS:
        src = root / d
        if any(src.rglob("*.md")):
            shutil.copytree(src, docs_dir / d, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".gitkeep"))
    # Assets for extra_css (optional, may not exist in all environments).
    assets_src = root / "tools" / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, docs_dir / "assets", dirs_exist_ok=True)

def _nav(docs_dir: Path) -> list:
    nav: list = [{"Home": "index.md"}]
    for d in CONTENT_DIRS:
        dd = docs_dir / d
        if not dd.exists():
            continue
        pages = [str(p.relative_to(docs_dir).as_posix()) for p in sorted(dd.rglob("*.md"))]
        if pages:
            nav.append({_TITLE_CAT[d]: pages})
    nav.append({"Graph ↗": GRAPH_URL})
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
        base["docs_dir"] = str(tmp / "docs")
        base["nav"] = _nav(tmp / "docs")
        (tmp / "mkdocs.yml").write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
        return subprocess.run(["mkdocs", "serve", "-f", str(tmp / "mkdocs.yml")], cwd=root).returncode
    out = build(root, root / "site")
    print(f"site -> {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

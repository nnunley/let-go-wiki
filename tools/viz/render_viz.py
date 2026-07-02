# tools/viz/render_viz.py
"""Standalone wrapper around the vendored OKF viewer (no GCP/reference_agent deps)."""
from __future__ import annotations
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generator import generate_visualization  # noqa: E402
from build_site import CONTENT_DIRS  # noqa: E402

def _stage_for_viz(root: Path, docs_dir: Path) -> None:
    """Stage only markdown content dirs for graph generation (skip assets)."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    # Copy index.md if it exists (optional for tests).
    index_src = root / "index.md"
    if index_src.exists():
        shutil.copy2(index_src, docs_dir / "index.md")
    for d in CONTENT_DIRS:
        src = root / d
        if any(src.rglob("*.md")):
            shutil.copytree(src, docs_dir / d, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".gitkeep"))

def render(bundle_root: Path, out: Path, name: str = "let-go-wiki") -> dict:
    """Render visualization from wiki content dirs only (excluding docs/ etc)."""
    bundle_root = Path(bundle_root)
    out = Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        staging_docs_dir = Path(tmp) / "docs"
        _stage_for_viz(bundle_root, staging_docs_dir)
        return generate_visualization(staging_docs_dir, out, bundle_name=name)

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

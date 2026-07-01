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

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

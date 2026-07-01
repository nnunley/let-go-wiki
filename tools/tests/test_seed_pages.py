from pathlib import Path
from tools.check_wiki import validate_page, _load_taxonomy_tags

ROOT = Path(__file__).resolve().parents[2]

def test_seed_pages_are_valid():
    tags = _load_taxonomy_tags(ROOT)
    for rel in ("entities/let-go.md", "concepts/stack-vm.md"):
        assert validate_page(ROOT / rel, tags) == []

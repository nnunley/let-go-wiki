import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def setup_wiki_taxonomy(tmp_path, monkeypatch):
    """Automatically set up wiki taxonomy in temp directory for all tests."""
    meta_dir = tmp_path / "_meta"
    meta_dir.mkdir()

    # Create a minimal taxonomy with known tags
    taxonomy = meta_dir / "taxonomy.md"
    taxonomy.write_text(
        "# Taxonomy\n\n- `go`\n- `vm`\n- `clojure`\n- `concept`\n- `entity`\n- `pattern`\n",
        encoding="utf-8"
    )

    # Set the working directory to tmp_path so _wiki_root can find taxonomy
    monkeypatch.chdir(tmp_path)

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

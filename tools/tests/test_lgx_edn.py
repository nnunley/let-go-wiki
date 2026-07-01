import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_lgx_edn_defines_required_tasks():
    text = (ROOT / "lgx.edn").read_text(encoding="utf-8")
    for task in ("doctor", "viz", "site", "serve"):
        assert re.search(rf"\b{task}\b", text), f"missing task {task}"
    # Balanced braces/brackets — cheap EDN sanity check.
    assert text.count("{") == text.count("}")
    assert text.count("[") == text.count("]")


def _lgx_cmd():
    """Return an argv prefix that runs lgx, or None if lgx is unavailable."""
    if shutil.which("lgx"):
        return ["lgx"]
    if shutil.which("mise"):
        try:
            r = subprocess.run(["mise", "exec", "--", "lgx", "version"],
                               cwd=ROOT, capture_output=True, timeout=60)
            if r.returncode == 0:
                return ["mise", "exec", "--", "lgx"]
        except (OSError, subprocess.SubprocessError):
            return None
    return None


def test_lgx_edn_is_valid_per_lgx():
    """When lgx is installed (directly or via mise), it must accept lgx.edn and
    list all four project tasks. Skipped where lgx is unavailable (e.g. CI)."""
    cmd = _lgx_cmd()
    if cmd is None:
        pytest.skip("lgx not available (install directly or via mise)")
    # `lgx help` prints project tasks only when lgx.edn is valid.
    r = subprocess.run(cmd + ["help"], cwd=ROOT, capture_output=True,
                       text=True, timeout=120)
    out = r.stdout + r.stderr
    assert "invalid lgx.edn" not in out, f"lgx rejected lgx.edn:\n{out}"
    for task in ("doctor", "viz", "site", "serve"):
        assert re.search(rf"lgx\s+{task}\b", out), f"task {task} not listed by lgx:\n{out}"

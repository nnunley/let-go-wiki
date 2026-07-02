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

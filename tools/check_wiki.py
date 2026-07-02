"""Validate let-go-wiki pages: required frontmatter, relative links, known tags."""
from __future__ import annotations
import re
import sys
from pathlib import Path
import yaml

REQUIRED_KEYS = ("type", "category", "title", "description", "tags", "status")
RESERVED = {"index.md", "log.md"}
_FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_ABS_LINK_RE = re.compile(r"\]\((/[^)]+\.md)\)")

def _load_taxonomy_tags(root: Path) -> set[str]:
    tax = root / "_meta" / "taxonomy.md"
    if not tax.exists():
        return set()
    return set(re.findall(r"^- `([a-z0-9-]+)`", tax.read_text(encoding="utf-8"), re.MULTILINE))

def _wiki_root(path: Path) -> Path:
    for p in [path, *path.parents]:
        if (p / "_meta" / "taxonomy.md").exists():
            return p
    # Fallback: check current working directory
    cwd = Path.cwd()
    if (cwd / "_meta" / "taxonomy.md").exists():
        return cwd
    return path.parent

def validate_page(path: Path, tags: set[str] | None = None) -> list[str]:
    if path.name in RESERVED:
        return []
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return [f"{path}: missing YAML frontmatter block"]
    errors: list[str] = []
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return [f"{path}: unparseable frontmatter: {e}"]
    for key in REQUIRED_KEYS:
        if key not in fm or fm[key] in (None, "", []):
            errors.append(f"{path}: missing/empty required key '{key}'")
    body = m.group(2)
    for lm in _ABS_LINK_RE.finditer(body):
        errors.append(f"{path}: absolute link '{lm.group(1)}' — use a file-relative link")
    known = tags if tags is not None else _load_taxonomy_tags(_wiki_root(path))
    page_tags = fm.get("tags") or []
    if not isinstance(page_tags, list):
        page_tags = [page_tags]
    if len(page_tags) > 5:
        errors.append(f"{path}: more than 5 tags")
    for t in page_tags:
        if known and t not in known:
            errors.append(f"{path}: unknown tag '{t}' (not in taxonomy)")
    return errors

def validate_tree(root: Path) -> dict[str, list[str]]:
    tags = _load_taxonomy_tags(root)
    content_dirs = ("concepts", "entities", "ideas", "projects", "sources", "references")
    out: dict[str, list[str]] = {}
    for d in content_dirs:
        for md in sorted((root / d).rglob("*.md")):
            errs = validate_page(md, tags)
            if errs:
                out[str(md.relative_to(root))] = errs
    return out

def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    results = validate_tree(root)
    if not results:
        print("check_wiki: OK")
        return 0
    for page, errs in results.items():
        for e in errs:
            print(e)
    return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

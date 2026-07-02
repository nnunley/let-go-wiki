"""Validate let-go-wiki pages: required frontmatter, relative links, known tags."""
from __future__ import annotations
import re
import sys
from pathlib import Path
import yaml
from markdown_it import MarkdownIt

REQUIRED_KEYS = ("type", "category", "title", "description", "tags", "status")
RESERVED = {"index.md", "log.md"}
_FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_ABS_LINK_RE = re.compile(r"\]\((/[^)]+\.md)\)")

def extract_links(markdown_body: str) -> list[str]:
    """Extract link destinations from markdown body using markdown-it-py."""
    md = MarkdownIt()
    tokens = md.parse(markdown_body)
    links = []

    def extract_from_tokens(token_list):
        for token in token_list:
            if token.type == "link_open":
                href = token.attrGet("href")
                if href:
                    links.append(href)
            if token.children:
                extract_from_tokens(token.children)

    extract_from_tokens(tokens)
    return links

def find_orphans(root: Path) -> list[Path]:
    """Find pages with no inbound links from index.md or other content pages."""
    content_dirs = ("concepts", "entities", "ideas", "projects", "sources", "references")

    # Collect all content pages
    all_pages: set[Path] = set()
    for d in content_dirs:
        for md in (root / d).rglob("*.md"):
            all_pages.add(md)

    # Collect all linked pages
    linked_pages: set[Path] = set()

    # Check index.md for links
    index_md = root / "index.md"
    if index_md.exists():
        text = index_md.read_text(encoding="utf-8")
        links = extract_links(text)
        for link in links:
            if link.endswith(".md") and not link.startswith("http"):
                target = root / link.lstrip("./")
                if target.exists():
                    linked_pages.add(target.resolve())

    # Check each content page for links
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        m = _FM_RE.match(text)
        if m:
            body = m.group(2)
        else:
            body = text

        links = extract_links(body)
        for link in links:
            if link.endswith(".md") and not link.startswith("http"):
                # Resolve relative to the linking page's directory
                target = (page.parent / link).resolve()
                if target.exists():
                    linked_pages.add(target.resolve())

    # Resolve all_pages to absolute paths for comparison
    all_pages_resolved = {p.resolve() for p in all_pages}

    # Find orphans
    orphans = all_pages_resolved - linked_pages
    return sorted([p for p in orphans])

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

    # Check for broken relative .md links
    links = extract_links(body)
    for link in links:
        # Skip absolute URLs and pure anchors
        if link.startswith("http://") or link.startswith("https://") or link.startswith("#"):
            continue
        # For .md links, check if the file exists
        if link.endswith(".md"):
            # Strip fragment if present
            link_path = link.split("#")[0]
            # Resolve relative to the page's directory
            target = (path.parent / link_path).resolve()
            if not target.exists():
                errors.append(f"{path}: broken link '{link}' (no such page)")

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
    orphans = find_orphans(root)

    # Report validation errors
    if results:
        for page, errs in results.items():
            for e in errs:
                print(e)

    # Report orphans
    if orphans:
        for orphan in orphans:
            orphan_rel = orphan.relative_to(root) if root in orphan.parents or orphan.parent == root else orphan
            print(f"{orphan_rel}: orphan page (no inbound links; add it to index.md)")

    if not results and not orphans:
        print("check_wiki: OK")
        return 0

    return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

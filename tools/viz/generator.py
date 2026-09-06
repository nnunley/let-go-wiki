from __future__ import annotations

import json
import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class OKFDocumentError(Exception):
    pass


class OKFDocument:
    def __init__(self, frontmatter, body):
        self.frontmatter = frontmatter
        self.body = body

    @staticmethod
    def parse(text: str) -> "OKFDocument":
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
        if not m:
            raise OKFDocumentError("no frontmatter")
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            raise OKFDocumentError(str(e))
        return OKFDocument(fm, m.group(2))

_INDEX_NAME = "index.md"
_LINK_RE = re.compile(r"\]\(([^)\s]+\.md)(?:#[A-Za-z0-9_\-]*)?\)")
_BODY_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_TYPE_PALETTE = {}


def _rewrite_body_links(body: str, concept_dir: str) -> str:
    """Rewrite relative .md links to MkDocs URLs (site-root-relative).

    For a concept in dir 'references/clojure.core', a body link like:
      [apply](apply.md) -> [apply](references/clojure.core/apply/)
      [fn](fn.md) -> [fn](references/clojure.core/fn/)
      [bar](../foo/bar.md) -> [bar](references/foo/bar/)
      [external](https://example.com) -> [external](https://example.com)  (unchanged)
      [anchor](#section) -> [anchor](#section)  (unchanged)
    """
    def replace_link(m):
        target = m.group(1)

        # Skip external URLs and absolute paths
        if "://" in target or target.startswith("/"):
            return m.group(0)

        # Skip anchor-only links
        if target.startswith("#"):
            return m.group(0)

        # Extract fragment (anchor) if present
        fragment = ""
        if "#" in target:
            target, fragment = target.split("#", 1)
            fragment = "#" + fragment

        # Skip if not ending in .md
        if not target.endswith(".md"):
            return m.group(0)

        # Normalize the path: resolve .. and . relative to concept_dir
        from pathlib import Path as PathlibPath
        concept_path = PathlibPath(concept_dir)
        link_path = concept_path / target

        # Normalize to remove .. and .
        try:
            # Use posixpath for consistent forward slashes
            import posixpath
            normalized = posixpath.normpath(link_path.as_posix())
            # Remove .md extension
            if normalized.endswith(".md"):
                normalized = normalized[:-3]
            # Create the MkDocs URL (ends with /)
            mkdocs_url = normalized + "/"
            return f"]({mkdocs_url}{fragment})"
        except Exception:
            # If anything fails, return original
            return m.group(0)

    return _BODY_LINK_RE.sub(replace_link, body)


# Each OKF type folds into one of six display kinds; the kind picks the node
# colour (light/dark pairs so nodes stay distinguishable on both page themes)
# and the legend entry. Function/Macro pages are stdlib references.
_TYPE_KIND = {
    "Entity": "Entity",
    "Concept": "Concept",
    "Reference": "Reference",
    "Function": "Reference",
    "Macro": "Reference",
    "Namespace": "Reference",
    "Package": "Project",
    "Project": "Project",
    "Idea": "Idea",
    "Source": "Source",
}
_KIND_PALETTE = {
    "Entity":    {"light": "#b45309", "dark": "#f5b041"},
    "Concept":   {"light": "#2e7d80", "dark": "#6cc0c3"},
    "Reference": {"light": "#5f7a1f", "dark": "#a9c65c"},
    "Project":   {"light": "#3f4fae", "dark": "#93a0ea"},
    "Idea":      {"light": "#8a3d8f", "dark": "#d494d8"},
    "Source":    {"light": "#a39477", "dark": "#6b5f47"},
}
_KIND_ORDER = ["Entity", "Concept", "Reference", "Project", "Idea", "Source"]
_DEFAULT_KIND = "Concept"
# Kept for callers/tests that read the legacy per-type map.
_TYPE_PALETTE = {t: _KIND_PALETTE[k]["light"] for t, k in _TYPE_KIND.items()}
_DEFAULT_NODE_COLOR = _KIND_PALETTE[_DEFAULT_KIND]["light"]


@dataclass
class Concept:
    id: str
    type: str
    title: str
    description: str
    resource: str
    tags: list[str]
    body: str
    status: str = ""
    links_to: list[str] = field(default_factory=list)
    cited_by: int = 0

    @property
    def kind(self) -> str:
        return _TYPE_KIND.get(self.type, _DEFAULT_KIND)

    def to_node(self) -> dict[str, Any]:
        kind = self.kind
        pal = _KIND_PALETTE[kind]
        # Size tracks how often a page is cited (its weight in the graph), not
        # body length: a long stub is still a leaf, a short hub is still a hub.
        size = 14 + min(30, 4 * self.cited_by)
        if kind == "Source":
            size = 12  # provenance nodes stay small and uniform
        return {
            "data": {
                "id": self.id,
                "label": self.title or self.id,
                "type": self.type,
                "kind": kind,
                "status": self.status,
                "description": self.description,
                "resource": self.resource,
                "tags": self.tags,
                "url": f"{self.id}/",
                "color": pal["light"],
                "colorDark": pal["dark"],
                "size": size,
                "citedBy": self.cited_by,
            }
        }


def _extract_links(body: str, doc_dir: Path, bundle_root: Path) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    bundle_root_resolved = bundle_root.resolve()
    for m in _LINK_RE.finditer(body):
        target = m.group(1)
        if "://" in target or target.startswith("/"):
            continue
        try:
            resolved = (doc_dir / target).resolve().relative_to(bundle_root_resolved)
        except ValueError:
            continue
        rel = resolved.as_posix()
        if rel.endswith(".md"):
            rel = rel[:-3]
        if rel and rel not in seen:
            seen.add(rel)
            out.append(rel)
    return out


def _walk_concepts(bundle_root: Path) -> list[Concept]:
    concepts: list[Concept] = []
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name == _INDEX_NAME:
            continue
        rel = md_path.relative_to(bundle_root).with_suffix("")
        concept_id = "/".join(rel.parts)
        try:
            doc = OKFDocument.parse(md_path.read_text(encoding="utf-8"))
        except OKFDocumentError:
            continue
        fm = doc.frontmatter or {}
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        # Rewrite body links from .md to MkDocs URLs
        body = doc.body or ""
        concept_dir = md_path.parent.relative_to(bundle_root).as_posix()
        body = _rewrite_body_links(body, concept_dir)

        concept = Concept(
            id=concept_id,
            type=str(fm.get("type") or "Unknown"),
            title=str(fm.get("title") or concept_id),
            description=str(fm.get("description") or ""),
            resource=str(fm.get("resource") or ""),
            tags=[str(t) for t in tags],
            body=body,
            status=str(fm.get("status") or ""),
            links_to=_extract_links(doc.body or "", md_path.parent, bundle_root),
        )
        concepts.append(concept)
    return concepts


def _build_graph(concepts: list[Concept]) -> dict[str, Any]:
    ids = {c.id for c in concepts}
    by_id = {c.id: c for c in concepts}
    for c in concepts:
        for target in c.links_to:
            if target != c.id and target in ids:
                by_id[target].cited_by += 1
    nodes = [c.to_node() for c in concepts]
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    for c in concepts:
        for target in c.links_to:
            if target == c.id or target not in ids:
                continue
            key = (c.id, target)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append({
                "data": {
                    "id": f"{c.id}__{target}",
                    "source": c.id,
                    "target": target,
                }
            })
    bodies = {c.id: c.body for c in concepts}
    types = sorted({c.type for c in concepts})
    kinds = [k for k in _KIND_ORDER if any(c.kind == k for c in concepts)]
    return {
        "nodes": nodes,
        "edges": edges,
        "bodies": bodies,
        "types": types,
        "kinds": kinds,
        "palette": _TYPE_PALETTE,
        "kindPalette": _KIND_PALETTE,
    }


def _load_template() -> str:
    template_path = Path(__file__).parent / "templates" / "viz.html"
    return template_path.read_text(encoding="utf-8")


def _load_asset(name: str) -> str:
    asset_path = Path(__file__).parent / "static" / name
    return asset_path.read_text(encoding="utf-8")


def generate_visualization(
    bundle_root: Path,
    out_path: Path,
    *,
    bundle_name: str | None = None,
) -> dict[str, int]:
    """Walk a bundle and write a single self-contained HTML visualization.

    Returns counts: {'concepts': N, 'edges': M, 'bytes': K}.
    """
    bundle_root = Path(bundle_root)
    out_path = Path(out_path)
    if not bundle_root.is_dir():
        raise FileNotFoundError(f"Bundle directory not found: {bundle_root}")

    concepts = _walk_concepts(bundle_root)
    graph = _build_graph(concepts)
    template = _load_template()
    css = _load_asset("viz.css")
    js = _load_asset("viz.js")
    name = bundle_name or bundle_root.resolve().name

    html = (
        template
        .replace("/*__VIZ_CSS__*/", css)
        .replace("/*__VIZ_JS__*/", js)
        .replace("__BUNDLE_NAME__", json.dumps(name))
        .replace("__BUNDLE_DATA__", json.dumps(graph))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    return {
        "concepts": len(concepts),
        "edges": len(graph["edges"]),
        "bytes": len(html.encode("utf-8")),
    }

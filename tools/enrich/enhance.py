"""Suggest enhancements to EXISTING wiki pages (the counterpart to next_batch).

A mechanical driver: it scores every page on cheap structural signals and emits
enhancement briefs, worst-first. Each brief separates **mechanical fixes** (thin
body, missing backlinks, promote-if-verified) from a **Needs review (LLM)**
worklist — the judgment-heavy items (promotion, staleness, grounding) that a
later LLM pass adjudicates. The driver routes; it does not decide.

Signals mirror prior art: llm_wiki's Lint pass (orphans, thin/uncited, missing
cross-refs) and the OKF driver's completeness counts (citations, sections),
including a no-regression guard (`regressed`) so a re-authored page never loses
citations or sections.
"""
from __future__ import annotations
import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wiki import extract_links, _FM_RE  # noqa: E402

CONTENT_DIRS = ("concepts", "entities", "ideas", "projects", "sources", "references")
_SPECULATIVE = "speculative"


def _parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(2)


def _iter_pages(root: Path):
    for d in CONTENT_DIRS:
        base = root / d
        if base.exists():
            for md in base.rglob("*.md"):
                if md.name not in ("index.md", "log.md"):
                    yield md


def _resolve_md_links(links, base_dir: Path) -> set[Path]:
    """Existing local .md link targets, resolved absolute."""
    out: set[Path] = set()
    for link in links:
        if link.startswith(("http://", "https://", "#")):
            continue
        lp = link.split("#", 1)[0]
        if lp.endswith(".md"):
            tgt = (base_dir / lp).resolve()
            if tgt.exists():
                out.add(tgt)
    return out


def citation_count(body: str) -> int:
    """Count entries under a `# Citations` / `## Citations` section."""
    n, in_sec = 0, False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("#"):
            in_sec = s.lstrip("#").strip().lower().startswith("citations")
            continue
        if in_sec and s and (s[0] in "-*[" or s.startswith("http")):
            n += 1
    return n


def section_names(body: str) -> set[str]:
    """Set of heading texts in the body (for regression checks)."""
    return {ln.lstrip("#").strip()
            for ln in body.splitlines() if ln.lstrip().startswith("#")}


def regressed(old_body: str, new_body: str) -> list[str]:
    """No-regression guard: what a re-authored page would LOSE (must be empty)."""
    problems: list[str] = []
    oc, nc = citation_count(old_body), citation_count(new_body)
    if nc < oc:
        problems.append(f"citations dropped {oc} -> {nc}")
    lost = section_names(old_body) - section_names(new_body)
    if lost:
        problems.append(f"sections removed: {sorted(lost)}")
    return problems


def build_signals(root: Path) -> list[dict]:
    root = Path(root)
    pages = list(_iter_pages(root))
    parsed = {p: _parse(p) for p in pages}
    inbound: Counter[Path] = Counter()
    outbound: dict[Path, set[Path]] = {}
    for p in pages:
        outs = _resolve_md_links(extract_links(parsed[p][1]), p.parent)
        outbound[p] = outs
        for t in outs:
            inbound[t] += 1
    idx = root / "index.md"
    if idx.exists():
        for t in _resolve_md_links(extract_links(idx.read_text(encoding="utf-8")), root):
            inbound[t] += 1

    signals: list[dict] = []
    for p in pages:
        fm, body = parsed[p]
        signals.append({
            "path": p.relative_to(root).as_posix(),
            "words": len(body.split()),
            "outbound": len(outbound[p]),
            "inbound": inbound[p.resolve()],
            "citations": citation_count(body),
            "sources": len(fm.get("sources") or []),
            "status": fm.get("status"),
            "type": fm.get("type"),
        })
    return signals


def _reasons(sig: dict, thin_words: int) -> list[str]:
    # Mechanical flags fire on genuine deficits (a lone source/inbound link is
    # normal, not a defect — those go to the softer LLM review worklist).
    r: list[str] = []
    if sig["words"] < thin_words:
        r.append(f"thin body ({sig['words']} words < {thin_words})")
    if sig["outbound"] == 0:
        r.append("no outbound links (disconnected)")
    if sig["inbound"] == 0:
        r.append("orphan (0 inbound)")
    if sig["citations"] == 0:
        r.append("no citations")
    if sig["sources"] == 0:
        r.append("no source")
    if sig["status"] == _SPECULATIVE:
        r.append("still speculative")
    return r


def _review_items(sig: dict) -> list[str]:
    """The judgment-heavy worklist routed to the LLM pass."""
    items: list[str] = []
    if sig["status"] == _SPECULATIVE:
        items.append("PROMOTE?: re-verify every claim against its source; "
                     "promote to stable if it holds.")
    if sig["sources"] <= 1:
        items.append("GROUNDING?: only one source — find a corroborating "
                     "source or confirm one is sufficient.")
    items.append("STALE?: re-check the cited source(s) for changes since this "
                 "page's `updated` date; reconcile any drift.")
    if sig["inbound"] <= 1:
        items.append("CONTRADICTION/OVERLAP?: check sibling pages on the same "
                     "topic for claims to cross-link or reconcile.")
    return items


def candidates(signals: list[dict], thin_words: int) -> list[dict]:
    ranked = []
    for sig in signals:
        reasons = _reasons(sig, thin_words)
        if reasons:
            ranked.append({**sig, "reasons": reasons, "score": len(reasons)})
    ranked.sort(key=lambda s: (-s["score"], s["words"]))  # score desc, then thinner first
    return ranked


def _render_brief(c: dict) -> str:
    fixes = "\n".join(f"- {r}" for r in c["reasons"])
    review = "\n".join(f"- {r}" for r in _review_items(c))
    return (
        f"# Enhancement brief: {c['path']}\n\n"
        f"- **score:** {c['score']}  "
        f"(words {c['words']} · in {c['inbound']} · out {c['outbound']} · "
        f"citations {c['citations']} · sources {c['sources']} · "
        f"status {c['status']})\n\n"
        f"## Mechanical fixes\n\n{fixes}\n\n"
        f"## Needs review (LLM)\n\n{review}\n\n"
        f"## Guard\n\n"
        f"When re-authoring, do NOT lose citations or sections "
        f"(`enhance.regressed(old, new)` must return []). Current floor: "
        f"{c['citations']} citations. Page must still pass "
        f"`python tools/check_wiki.py .`.\n"
    )


def write_briefs(root: Path, count: int, out_dir: Path, thin_words: int) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ranked = candidates(build_signals(root), thin_words)[:count]
    written = []
    for c in ranked:
        brief = out_dir / (c["path"].replace("/", "__").replace(".md", "") + ".md")
        brief.write_text(_render_brief(c), encoding="utf-8")
        written.append(brief)
    return written


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-enhance")
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--count", type=int, default=8)
    p.add_argument("--out", type=Path, default=Path(".enrich/enhance"))
    p.add_argument("--thin-words", type=int, default=120,
                   help="Bodies below this word count are flagged thin.")
    p.add_argument("--report-only", action="store_true",
                   help="Print the ranked report without writing briefs.")
    args = p.parse_args(argv)

    ranked = candidates(build_signals(args.root), args.thin_words)
    print(f"enhance: {len(ranked)} page(s) with enhancement signals "
          f"(of {len(list(_iter_pages(args.root)))} total)\n")
    for c in ranked[:args.count]:
        print(f"  [{c['score']}] {c['path']}")
        print(f"        {', '.join(c['reasons'])}")
    if not args.report_only:
        briefs = write_briefs(args.root, args.count, args.out, args.thin_words)
        print(f"\nwrote {len(briefs)} brief(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

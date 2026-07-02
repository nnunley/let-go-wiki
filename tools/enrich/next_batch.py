"""Generate per-concept authoring briefs for the next batch of pending concepts."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.coverage import authored_ids, page_path_for  # noqa: E402

_TAG_RE = re.compile(r"^- `([a-z0-9-]+)`", re.MULTILINE)


def _tags(root: Path) -> list[str]:
    tax = root / "_meta" / "taxonomy.md"
    return _TAG_RE.findall(tax.read_text(encoding="utf-8")) if tax.exists() else []


def next_briefs(manifest_path: Path, root: Path, count: int, out_dir: Path) -> list[Path]:
    root, out_dir = Path(root), Path(out_dir)
    records = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    have = authored_ids(root)
    by_ns: dict[str, list[str]] = {}
    for r in records:
        by_ns.setdefault(r["ns"], []).append(r["id"])
    tags = _tags(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for r in records:
        if len(written) >= count:
            break
        if r["id"] in have:
            continue
        siblings = [i for i in by_ns.get(r["ns"], []) if i != r["id"]][:40]
        brief = out_dir / (r["id"].replace("/", "__") + ".md")
        brief.write_text(_render_brief(r, tags, siblings), encoding="utf-8")
        written.append(brief)
    return written


def _render_brief(r: dict, tags: list[str], siblings: list[str]) -> str:
    return (
        f"# Authoring brief: {r['id']}\n\n"
        f"- **Target page:** `{page_path_for(r['id'], r['kind'])}`\n"
        f"- **kind:** {r['kind']}\n- **ns:** {r['ns']}\n- **name:** {r['name']}\n"
        f"- **signature:** `{r['signature']}`\n"
        f"- **source_path:** {r['source_path']}\n\n"
        f"## Docstring (from source — ground the page in this, do not contradict)\n\n"
        f"{r.get('doc') or '(none)'}\n\n"
        f"## Allowed tags (choose ≤5 from _meta/taxonomy.md)\n\n"
        + ", ".join(tags) + "\n\n"
        f"## Sibling concept ids (same ns — link with file-relative `.md` links)\n\n"
        + "\n".join(f"- {s}" for s in siblings) + "\n\n"
        f"## Instructions\n\n"
        f"Follow `tools/enrich/prompts/reference_instruction.md`. Construct 1–3 example\n"
        f"forms, evaluate each with `lg -e '<form>'`, and use the REAL output (never\n"
        f"invented). Write the page at the target path; it must pass\n"
        f"`python tools/check_wiki.py .`. status: speculative.\n"
    )


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-next")
    p.add_argument("--manifest", type=Path, default=Path(".enrich/manifest.json"))
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--out", type=Path, default=Path(".enrich/briefs"))
    args = p.parse_args(argv)
    briefs = next_briefs(args.manifest, args.root, args.count, args.out)
    print(f"enrich next: wrote {len(briefs)} brief(s) -> {args.out}")
    for b in briefs:
        print(f"  {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

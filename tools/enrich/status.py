"""Report wiki authoring coverage against the enrich manifest."""
from __future__ import annotations
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.coverage import coverage  # noqa: E402


def render_status(cov: dict, sample: int = 10) -> str:
    lines = [f"coverage: {cov['authored']}/{cov['total']} concepts authored "
             f"({len(cov['pending'])} pending)"]
    if cov["pending"]:
        lines.append("next pending:")
        lines += [f"  - {pid}" for pid in cov["pending"][:sample]]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-status")
    p.add_argument("--manifest", type=Path, default=Path(".enrich/manifest.json"))
    p.add_argument("--root", type=Path, default=Path("."))
    args = p.parse_args(argv)
    if not args.manifest.exists():
        print(f"no manifest at {args.manifest}; run `lgx enrich` first", file=sys.stderr)
        return 1
    print(render_status(coverage(args.manifest, args.root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

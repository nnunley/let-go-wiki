"""Build the per-concept work manifest that the Plan C authoring loop consumes."""
from __future__ import annotations
import argparse, json, sys, tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from letgo_source import LetGoSource  # noqa: E402


def prepare(config_path: Path, out_dir: Path, source_root: Path, lg=None) -> Path:
    config_path, out_dir, source_root = map(Path, (config_path, out_dir, source_root))
    cfg = tomllib.loads(config_path.read_text(encoding="utf-8"))
    src = LetGoSource(lg_cmd=lg)
    records: list[dict] = []
    for entry in cfg.get("source", []):
        source_file = source_root / entry["file"]
        for c in src.list_concepts(source_file, ns=entry["ns"]):
            detail = src.read_concept(c)
            records.append({
                "id": detail["id"], "kind": detail["kind"], "name": detail["name"],
                "ns": detail["ns"], "signature": detail["signature"],
                "doc": detail["doc"], "source_path": str(source_file),
                "status": "pending",
            })
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="enrich-prepare")
    p.add_argument("--source-root", required=True, type=Path,
                   help="Path to the let-go checkout")
    p.add_argument("--config", type=Path,
                   default=Path(__file__).resolve().parent / "config.toml")
    p.add_argument("--out", type=Path, default=Path(".enrich"))
    args = p.parse_args(argv)
    manifest = prepare(args.config, args.out, args.source_root)
    records = json.loads(manifest.read_text(encoding="utf-8"))
    print(f"enrich: {len(records)} concepts -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

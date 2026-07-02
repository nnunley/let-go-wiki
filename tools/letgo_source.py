"""Enumerate let-go stdlib concepts by reading .lg source via let-go's reader,
and evaluate example forms via `lg -e`. Runtime var introspection is thin, so
this reads source rather than reflecting."""
from __future__ import annotations
import json, shutil, subprocess
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ENUMERATE = _ROOT / "letgo" / "enumerate.lg"
_KIND = {"defn": "Function", "defn-": "Function", "definline": "Function",
         "defmacro": "Macro", "def": "Var"}


def resolve_lg() -> list[str] | None:
    """argv prefix that runs the `lg` binary, or None if unavailable."""
    if shutil.which("lg"):
        return ["lg"]
    if shutil.which("mise"):
        try:
            r = subprocess.run(["mise", "exec", "--", "lg", "-e", "nil"],
                               capture_output=True, timeout=60)
            if r.returncode == 0:
                return ["mise", "exec", "--", "lg"]
        except (OSError, subprocess.SubprocessError):
            return None
    return None


@dataclass
class Concept:
    id: str
    kind: str
    name: str
    ns: str
    arglists: list[list[str]] = field(default_factory=list)
    doc: str | None = None
    private: bool = False
    source_path: str = ""


class LetGoSourceError(RuntimeError):
    pass


class LetGoSource:
    def __init__(self, lg_cmd: list[str] | None = None):
        self.lg = lg_cmd or resolve_lg()
        if self.lg is None:
            raise LetGoSourceError("lg binary not available")

    def _enumerate(self, source_file: Path) -> list[dict]:
        r = subprocess.run(self.lg + [str(_ENUMERATE), str(source_file)],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise LetGoSourceError(f"enumerate.lg failed for {source_file}: {r.stderr}")
        out = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                out.append(json.loads(line))
        return out

    def list_concepts(self, source_file: Path, ns: str) -> list[Concept]:
        concepts = []
        for f in self._enumerate(Path(source_file)):
            kind = _KIND.get(f["op"], "Var")
            concepts.append(Concept(
                id=f"{ns}/{f['name']}",
                kind=kind, name=f["name"], ns=ns,
                arglists=f.get("arglists") or [],
                doc=f.get("doc"),
                private=bool(f.get("private")),
                source_path=str(source_file),
            ))
        return concepts

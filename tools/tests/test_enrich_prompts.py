from pathlib import Path

P = Path(__file__).resolve().parents[1] / "enrich" / "prompts"

def _read(name):
    return (P / name).read_text(encoding="utf-8").lower()

def test_reference_prompt_has_letgo_contract():
    t = _read("reference_instruction.md")
    for needle in ["# signature", "# examples", "# citations",
                   "file-relative", "status: speculative", "lg -e"]:
        assert needle in t, f"reference prompt missing: {needle}"
    # Must NOT carry over BigQuery/SQL specifics.
    for banned in ["bigquery", "sql", "# schema"]:
        assert banned not in t, f"reference prompt still mentions: {banned}"

def test_web_prompt_keeps_four_gates_and_letgo_extractions():
    t = _read("web_ingestion_instruction.md")
    for needle in ["four gate", "references/", "skip",
                   "clojure-compat", "interop", "limitation"]:
        assert needle in t, f"web prompt missing: {needle}"

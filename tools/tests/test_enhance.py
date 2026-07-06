from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enrich.enhance import (  # noqa: E402
    build_signals, candidates, citation_count, section_names, regressed,
    write_briefs, main,
)

def _write(p: Path, fm: str, body: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")
    return p

_FM = ('type: Concept\ncategory: concept\ntitle: "T"\ndescription: "d"\n'
       'tags: [go]\nstatus: {status}\nsources: {sources}')

def _make_tree(tmp_path):
    # rich page: long body, links to thin, many citations, 2 sources, stable
    rich_body = ("word " * 300) + "\n\n[thin](thin.md)\n\n# Citations\n- [a](x)\n- [b](y)\n- [c](z)\n"
    _write(tmp_path / "concepts" / "rich.md",
           _FM.format(status="stable", sources='["s1", "s2"]'), rich_body)
    # thin page: short, no outbound, no citations, 0 sources, speculative
    _write(tmp_path / "concepts" / "thin.md",
           _FM.format(status="speculative", sources="[]"), "short body only")
    # index links rich (so rich has inbound; thin is near-orphan except rich->thin)
    (tmp_path / "index.md").write_text("# I\n\n- [rich](concepts/rich.md)\n", encoding="utf-8")
    return tmp_path

def test_build_signals_computes_metrics(tmp_path):
    _make_tree(tmp_path)
    sigs = {s["path"]: s for s in build_signals(tmp_path)}
    assert sigs["concepts/rich.md"]["citations"] == 3
    assert sigs["concepts/rich.md"]["outbound"] == 1        # -> thin
    assert sigs["concepts/rich.md"]["inbound"] == 1         # from index
    assert sigs["concepts/thin.md"]["citations"] == 0
    assert sigs["concepts/thin.md"]["inbound"] == 1         # from rich
    assert sigs["concepts/thin.md"]["words"] < 10

def test_candidates_flags_thin_page_first(tmp_path):
    _make_tree(tmp_path)
    ranked = candidates(build_signals(tmp_path), thin_words=120)
    assert ranked[0]["path"] == "concepts/thin.md"
    reasons = " ".join(ranked[0]["reasons"])
    assert "thin body" in reasons and "speculative" in reasons and "no citations" in reasons

def test_rich_page_has_fewer_or_no_signals(tmp_path):
    _make_tree(tmp_path)
    ranked = {c["path"]: c for c in candidates(build_signals(tmp_path), thin_words=120)}
    # rich still near-orphan (1 inbound) but not thin/uncited/speculative
    rich = ranked.get("concepts/rich.md")
    if rich:
        joined = " ".join(rich["reasons"])
        assert "thin body" not in joined and "speculative" not in joined

def test_citation_count_and_sections():
    body = "# Overview\ntext\n\n# Citations\n- [a](x)\nhttp://b\n\ntrailing"
    assert citation_count(body) == 2
    assert section_names(body) == {"Overview", "Citations"}

def test_regressed_detects_dropped_citations_and_sections():
    old = "# A\n\n# Citations\n- [1](x)\n- [2](y)\n"
    new = "# Citations\n- [1](x)\n"   # lost section A and one citation
    probs = regressed(old, new)
    assert any("citations dropped" in p for p in probs)
    assert any("sections removed" in p for p in probs)
    assert regressed(old, old) == []

def test_write_briefs_and_main(tmp_path):
    _make_tree(tmp_path)
    briefs = write_briefs(tmp_path, count=5, out_dir=tmp_path / ".enrich" / "enhance", thin_words=120)
    assert briefs, "expected at least one brief"
    txt = (tmp_path / ".enrich" / "enhance" / "concepts__thin.md").read_text()
    assert "Mechanical fixes" in txt and "Needs review (LLM)" in txt and "Guard" in txt
    assert main(["--root", str(tmp_path), "--report-only"]) == 0

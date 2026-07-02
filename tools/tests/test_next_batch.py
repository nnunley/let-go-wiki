import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.enrich.next_batch import next_briefs  # noqa: E402

def _manifest(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps([
        {"id":"clojure.core/map","kind":"Function","name":"map","ns":"clojure.core",
         "signature":"(map [f coll])","doc":"Apply f.","source_path":"core.lg"},
        {"id":"clojure.core/filter","kind":"Function","name":"filter","ns":"clojure.core",
         "signature":"(filter [pred coll])","doc":"Keep matching.","source_path":"core.lg"},
    ]), encoding="utf-8")
    return m

def test_next_writes_one_brief_per_pending(tmp_path):
    (tmp_path / "_meta" / "taxonomy.md").write_text("- `stdlib`\n- `clojure`\n", encoding="utf-8")
    briefs = next_briefs(_manifest(tmp_path), tmp_path, count=2, out_dir=tmp_path/"briefs")
    assert len(briefs) == 2
    text = (tmp_path/"briefs"/"clojure.core__map.md").read_text(encoding="utf-8")
    assert "(map [f coll])" in text                       # signature
    assert "references/clojure.core/map.md" in text        # target path
    assert "clojure.core/filter" in text                  # sibling id
    assert "stdlib" in text                                # taxonomy tag offered

def test_next_skips_already_authored(tmp_path):
    (tmp_path/"_meta"/"taxonomy.md").write_text("- `stdlib`\n", encoding="utf-8")
    (tmp_path / "references" / "clojure.core").mkdir(parents=True)
    (tmp_path / "references" / "clojure.core" / "map.md").write_text("x", encoding="utf-8")
    briefs = next_briefs(_manifest(tmp_path), tmp_path, count=5, out_dir=tmp_path/"briefs")
    names = {b.name for b in briefs}
    assert names == {"clojure.core__filter.md"}           # map already authored → skipped

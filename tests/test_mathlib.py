import json, pathlib
from harvesters.mathlib.harvest import harvest

FIX = pathlib.Path(__file__).parent / "fixtures" / "mathlib_decls_small.json"

def test_harvest_maps_kinds_and_urls(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    rows = [json.loads(l) for l in (tmp_path / "statements.jsonl").read_text().splitlines()]
    assert man["statement_count"] == len(rows) > 0
    kinds = {r["kind"] for r in rows}
    assert kinds <= {"theorem", "definition", "lemma", "other"}
    for r in rows:
        assert r["source_url"].startswith("https://leanprover-community.github.io/mathlib4_docs/")
        assert r["module"]

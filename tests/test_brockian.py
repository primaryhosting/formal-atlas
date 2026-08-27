import json, pathlib
import pytest
from harvesters.brockian.harvest import harvest

FIX = pathlib.Path(__file__).parent / "fixtures" / "brockian_registry_small.json"

def test_harvests_only_proved_sorry_free(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    rows = [json.loads(l) for l in (tmp_path / "statements.jsonl").read_text().splitlines()]
    assert man["statement_count"] == 2
    assert all(r["library"] == "brockian" for r in rows)
    assert all(r["source_url"].startswith("https://torus.riemannlab.com") for r in rows)
    assert all(r["subject_codes"] == ["11"] for r in rows)  # Brockian.AbundantClosure -> 11
    assert man["subject_derivation"].startswith("MSC 2020")

def test_module_becomes_module_and_kind_maps(tmp_path):
    harvest(source=str(FIX), out_dir=tmp_path)
    rows = [json.loads(l) for l in (tmp_path / "statements.jsonl").read_text().splitlines()]
    r = rows[0]
    assert r["module"] and r["kind"] in {"theorem", "definition", "lemma", "axiom", "other"}

def test_missing_theorems_key_raises(tmp_path):
    src = tmp_path / "registry.json"
    src.write_text(json.dumps({"schema": "brockian-public-verified-registry/v1"}))
    with pytest.raises(SystemExit, match="missing 'theorems'"):
        harvest(source=str(src), out_dir=tmp_path / "out")

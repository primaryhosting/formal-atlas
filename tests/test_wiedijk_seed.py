import pathlib, yaml
from tools.build_wiedijk_seed import build_seed

FIX = pathlib.Path(__file__).parent / "fixtures" / "mathlib_100_small.yaml"

def test_build_seed_concepts_and_alignments(tmp_path):
    out = tmp_path / "wiedijk100.yaml"
    build_seed(source=str(FIX), out=str(out))
    doc = yaml.safe_load(out.read_text())
    assert doc["seed_source"] == "wiedijk100"
    concepts = doc["concepts"]
    assert len(concepts) == 3
    c = concepts[0]
    assert set(c) >= {"slug", "title", "wiedijk_number", "status", "alignments"}
    formalized = [c for c in concepts if c["alignments"]]
    assert formalized
    for c in formalized:
        a = c["alignments"][0]
        assert a["library"] == "mathlib" and a["tier"] == "CURATED"
        assert a["evidence"]["source"] == "mathlib4 docs/100.yaml"
    unformalized = [c for c in concepts if not c["alignments"]]
    assert all(c["status"] == "open" for c in unformalized)

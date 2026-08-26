import json, pathlib, pytest
from atlas.emit import write_harvest

def _stmt(name="Foo.bar"):
    return {"library": "brockian", "native_name": name, "kind": "theorem",
            "statement_text": "x = x", "module": "Foo", "subject_codes": [],
            "source_url": "https://torus.riemannlab.com/explore/lean-registry"}

def test_write_harvest_emits_jsonl_and_manifest(tmp_path):
    out = write_harvest(tmp_path, "brockian", [_stmt(), _stmt("Foo.baz")],
                        harvester_version="0.0.1", source_version="test-v1")
    lines = (tmp_path / "statements.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2
    man = json.loads((tmp_path / "manifest.json").read_text())
    assert man["statement_count"] == 2
    assert man["library"] == "brockian"
    assert len(man["sha256"]) == 64

def test_write_harvest_rejects_invalid_statement(tmp_path):
    bad = _stmt(); del bad["source_url"]
    with pytest.raises(Exception):
        write_harvest(tmp_path, "brockian", [bad],
                      harvester_version="0.0.1", source_version="test-v1")

def test_write_harvest_rejects_duplicate_native_name(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        write_harvest(tmp_path, "brockian", [_stmt(), _stmt()],
                      harvester_version="0.0.1", source_version="test-v1")

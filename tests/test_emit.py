import hashlib, json, pathlib, pytest
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

def test_write_harvest_empty_corpus(tmp_path):
    man = write_harvest(tmp_path, "brockian", [],
                        harvester_version="0.0.1", source_version="test-v1")
    assert (tmp_path / "statements.jsonl").read_bytes() == b""
    assert man["statement_count"] == 0
    assert man["sha256"] == hashlib.sha256(b"").hexdigest()

def test_write_harvest_output_is_order_independent(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    man_ab = write_harvest(a, "brockian", [_stmt("Foo.bar"), _stmt("Foo.baz")],
                           harvester_version="0.0.1", source_version="test-v1")
    man_ba = write_harvest(b, "brockian", [_stmt("Foo.baz"), _stmt("Foo.bar")],
                           harvester_version="0.0.1", source_version="test-v1")
    assert (a / "statements.jsonl").read_bytes() == (b / "statements.jsonl").read_bytes()
    assert man_ab["sha256"] == man_ba["sha256"]

import json
import pathlib
import re

import pytest
import yaml

from tools.build_targets_seed import build_seed

FIX = pathlib.Path(__file__).parent / "fixtures" / "targets_board.json"


def _built(tmp_path):
    out = tmp_path / "targets-board.yaml"
    build_seed(source=str(FIX), out=str(out))
    return yaml.safe_load(out.read_text())


def test_build_seed_shape_and_measured_counts(tmp_path):
    doc = _built(tmp_path)
    assert doc["seed_source"] == "targets-board"
    concepts = doc["concepts"]

    board = json.loads(FIX.read_text())
    assert len(concepts) == len(board["problems"])  # full board, no rows dropped

    # Measured alignment count must equal the fixture's own brockian rows —
    # never trust the board's meta block.
    fixture_aligned = sum(1 for p in board["problems"] if p["brockian"])
    aligned = [c for c in concepts if c["alignments"]]
    assert len(aligned) == fixture_aligned


def test_slugs_are_target_nnn_and_unique(tmp_path):
    concepts = _built(tmp_path)["concepts"]
    slugs = [c["slug"] for c in concepts]
    assert len(slugs) == len(set(slugs))
    for slug in slugs:
        assert re.fullmatch(r"target-\d{3}-[a-z0-9]+(-[a-z0-9]+)*", slug), slug
    assert concepts[0]["slug"] == "target-001-riemann-hypothesis"


def test_alignment_shape_and_status(tmp_path):
    concepts = _built(tmp_path)["concepts"]
    for c in concepts:
        if c["alignments"]:
            assert c["status"] == "partially-formalized"
            (a,) = c["alignments"]
            assert a["library"] == "brockian"
            assert a["tier"] == "CURATED"
            assert a["evidence"] == {"source": "riemannlab targets board"}
            assert a["native_name"].startswith("Brockian.")
        else:
            assert c["status"] == "open"
            assert c["alignments"] == []


def test_informal_statement_copied_from_board(tmp_path):
    concepts = _built(tmp_path)["concepts"]
    board = json.loads(FIX.read_text())
    by_board_id = {c["board_id"]: c for c in concepts}
    for p in board["problems"]:
        assert by_board_id[p["id"]]["informal_statement"] == p["statement"]


def test_board_status_preserved_verbatim(tmp_path):
    concepts = _built(tmp_path)["concepts"]
    board = json.loads(FIX.read_text())
    by_board_id = {c["board_id"]: c for c in concepts}
    for p in board["problems"]:
        assert by_board_id[p["id"]]["board_status"] == p["status"]


def test_blank_statement_and_blank_brockian(tmp_path):
    src = tmp_path / "board.json"
    src.write_text(json.dumps({
        "meta": {"as_of": "2026-08-06"},
        "problems": [
            {"id": "a", "name": "No Statement", "field": "nt", "statement": "",
             "status": "open", "prize": "", "brockian": "  ", "resolved": "", "note": ""},
        ],
    }))
    out = tmp_path / "out.yaml"
    build_seed(source=str(src), out=str(out))
    (c,) = yaml.safe_load(out.read_text())["concepts"]
    assert c["informal_statement"] is None
    assert c["status"] == "open"
    assert c["alignments"] == []


def test_missing_problems_key_raises(tmp_path):
    src = tmp_path / "board.json"
    src.write_text(json.dumps({"meta": {"as_of": "2026-08-06"}}))
    with pytest.raises(ValueError, match="problems"):
        build_seed(source=str(src), out=str(tmp_path / "out.yaml"))

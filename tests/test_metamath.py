import json, pathlib
import pytest
from harvesters.metamath.harvest import parse_mm, harvest

FIX = pathlib.Path(__file__).parent / "fixtures" / "set_mm_excerpt.mm"

def test_parse_extracts_labels_kinds_sections():
    rows = list(parse_mm(FIX.read_text().splitlines()))
    by = {r["native_name"]: r for r in rows}
    assert by["id"]["kind"] == "theorem"
    assert by["ax-1"]["kind"] == "axiom"
    assert by["df-bi"]["kind"] == "definition"
    assert by["id"]["module"] == "Propositional calculus"
    assert "ph -> ph" in by["id"]["statement_text"]

def test_finer_section_banner_overrides_coarse():
    rows = list(parse_mm(FIX.read_text().splitlines()))
    by = {r["native_name"]: r for r in rows}
    # mpbi sits after a =-=- (Section) banner that follows the #*#* (Part) one.
    assert by["mpbi"]["module"] == "Logical equivalence"

def test_unterminated_comment_at_eof_raises():
    with pytest.raises(ValueError, match="unterminated construct at EOF"):
        list(parse_mm(["$( this comment never closes"]))

def test_harvest_emits_valid_output(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    assert man["library"] == "metamath"
    assert man["statement_count"] == 4
    rows = [json.loads(l) for l in (tmp_path / "statements.jsonl").read_text().splitlines()]
    assert all(r["source_url"] == f"https://us.metamath.org/mpeuni/{r['native_name']}.html" for r in rows)

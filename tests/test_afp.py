import json, pathlib
import pytest
from harvesters.afp.harvest import parse_entries, harvest

FIX = pathlib.Path(__file__).parent / "fixtures" / "afp_entries_index_excerpt.json"


def _rows():
    return list(parse_entries(json.loads(FIX.read_text())))


def test_parse_one_row_per_entry_with_entry_level_fields():
    rows = _rows()
    assert len(rows) == 6  # fixture holds 6 real entries, verbatim slice of /entries/index.json
    by = {r["native_name"]: r for r in rows}
    r = by["Laurent_Annulus"]
    assert r["library"] == "afp"
    assert r["kind"] == "other"  # entry-level harvest: an AFP entry is not a single theorem
    assert r["statement_text"] == "Laurent Series Expansions on an Annulus"
    assert r["source_url"] == "https://www.isa-afp.org/entries/Laurent_Annulus.html"


def test_topics_become_module_and_subject_codes():
    by = {r["native_name"]: r for r in _rows()}
    r = by["Laurent_Annulus"]
    assert r["module"] == "Mathematics/Analysis"      # first AFP topic tag
    assert r["subject_codes"] == ["Mathematics/Analysis"]
    # Miquel is tagged with a geometry topic in the real index
    assert any("Geometry" in c for c in by["Miquel"]["subject_codes"])


def test_missing_shortname_raises():
    with pytest.raises(ValueError, match="shortname"):
        list(parse_entries([{"title": "No name here"}]))


def test_non_list_index_raises():
    with pytest.raises(ValueError, match="expected a JSON array"):
        list(parse_entries({"shortname": "X"}))


def test_harvest_emits_valid_output(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    assert man["library"] == "afp"
    assert man["statement_count"] == 6
    assert man["subject_derivation"] == "AFP topic tags"
    rows = [json.loads(l) for l in (tmp_path / "statements.jsonl").read_text().splitlines()]
    assert all(r["kind"] == "other" for r in rows)
    assert all(r["source_url"].startswith("https://www.isa-afp.org/entries/") for r in rows)

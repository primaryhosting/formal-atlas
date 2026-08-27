"""Golden-file test: metamath parser vs a real ~150 KB head of set.mm.

Fixture: tests/fixtures/set_mm_head.mm — first 150,001 bytes of upstream
set.mm (develop), truncated at the last complete top-level statement (see the
provenance comment inside the fixture). Every expected number below was
computed by an INDEPENDENT token-level counter (comment-stripping state
machine, no shared code with parse_mm) and the five spot-check labels were
verified by eye against the raw fixture text — this is a golden file, not a
parser-echo.
"""
import json
import pathlib

import pytest

from harvesters.metamath.harvest import harvest, parse_mm

FIX = pathlib.Path(__file__).parent / "fixtures" / "set_mm_head.mm"

# Independent count: 8 $a + 354 $p statements outside comments.
EXPECTED_TOTAL = 362
EXPECTED_KINDS = {"theorem": 354, "axiom": 7, "definition": 1}
# The 8 $a labels, verified by eye: wn wi wb (syntax -> axiom),
# ax-mp ax-1 ax-2 ax-3 (axiom), df-bi (definition).
EXPECTED_AXIOM_LABELS = {"wn", "wi", "wb", "ax-mp", "ax-1", "ax-2", "ax-3"}

# Spot checks read directly from the fixture text (label line / nearest
# preceding #*#* or =-=- banner), NOT from parser output:
#   wn     line  573, banner line 560  "Recursively define primitive wffs..."
#   ax-mp  line  671, banner line 623  "The axioms of propositional calculus"
#   id     line  881, banner line 709  "Logical implication"
#   df-bi  line 2510, banner line 2414 "Logical equivalence"
#   con2b  line 3785 (last statement), same "Logical equivalence" section
SPOT = {
    "wn": ("axiom", "Recursively define primitive wffs for propositional calculus"),
    "ax-mp": ("axiom", "The axioms of propositional calculus"),
    "id": ("theorem", "Logical implication"),
    "df-bi": ("definition", "Logical equivalence"),
    "con2b": ("theorem", "Logical equivalence"),
}


@pytest.fixture(scope="module")
def rows():
    return list(parse_mm(FIX.read_text(encoding="utf-8").splitlines()))


def test_exact_statement_count(rows):
    assert len(rows) == EXPECTED_TOTAL


def test_exact_kind_breakdown(rows):
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    assert kinds == EXPECTED_KINDS
    assert {r["native_name"] for r in rows if r["kind"] != "theorem"} \
        == EXPECTED_AXIOM_LABELS | {"df-bi"}


def test_spot_check_labels(rows):
    by = {r["native_name"]: r for r in rows}
    for label, (kind, module) in SPOT.items():
        assert by[label]["kind"] == kind, label
        assert by[label]["module"] == module, label


def test_no_duplicate_labels_and_document_order_endpoints(rows):
    names = [r["native_name"] for r in rows]
    assert len(names) == len(set(names))
    # idi is the first statement in set.mm's head; the fixture's truncation
    # point is con2b (its provenance comment says so).
    assert names[0] == "idi"
    assert names[-1] == "con2b"


def test_statement_text_matches_source(rows):
    by = {r["native_name"]: r for r in rows}
    # Read straight off the fixture lines quoted in SPOT's comment above.
    assert by["ax-mp"]["statement_text"] == "|- ps"
    assert by["id"]["statement_text"] == "|- ( ph -> ph )"
    assert by["con2b"]["statement_text"] \
        == "|- ( ( ph -> -. ps ) <-> ( ps -> -. ph ) )"


def test_harvest_round_trips_through_emit(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    assert man["library"] == "metamath"
    assert man["statement_count"] == EXPECTED_TOTAL
    lines = (tmp_path / "statements.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == EXPECTED_TOTAL
    rows_out = [json.loads(l) for l in lines]
    assert all(
        r["source_url"] == f"https://us.metamath.org/mpeuni/{r['native_name']}.html"
        for r in rows_out)

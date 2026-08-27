"""Tests for the frontier nominator (pure logic — no network).

The live PostgREST reads run only in the tool's __main__; here every input
(board concepts, wiedijk concepts, live alignment counts, generation date) is
injected as a fixture. Spec: docs/2026-08-27-proving-flywheel-spec.md.
"""
import pathlib

import yaml

from tools.nominate_frontier import (
    ENGINE_READY,
    NOT_ATTACKABLE,
    build_nominations,
    count_noncandidate,
    normalize_title,
)

REPO = pathlib.Path(__file__).resolve().parent.parent

GEN_AT = "2026-08-27T00:00:00+00:00"


def _board(slug, title, *, board_status="open", status="open", brockian=None):
    alignments = []
    if brockian:
        alignments.append({"library": "brockian", "native_name": brockian,
                           "tier": "CURATED",
                           "evidence": {"source": "riemannlab targets board"}})
    return {"slug": slug, "title": title, "board_status": board_status,
            "status": status, "alignments": alignments}


def _wiedijk(slug, title, number, *, status="open"):
    return {"slug": slug, "title": title, "wiedijk_number": number,
            "status": status}


B_MAGIC = _board("target-098-3-3-magic-square-of-squares",
                 "3×3 Magic Square of Squares")
B_RAMSEY = _board("target-084-ramsey-number-r-5-5", "Ramsey Number R(5,5)")
B_HODGE = _board("target-003-hodge-conjecture", "Hodge Conjecture")
B_GOLDBACH = _board("target-008-goldbach-s-conjecture", "Goldbach’s Conjecture",
                    status="partially-formalized",
                    brockian="Brockian.GoldbachComb")
B_LONELY = _board("target-033-lonely-runner-conjecture",
                  "Lonely Runner Conjecture")
B_FLT = _board("target-036-fermat-s-last-theorem", "Fermat’s Last Theorem",
               board_status="resolved")
B_ABC = _board("target-030-abc-conjecture", "abc Conjecture",
               board_status="disputed")
B_CH = _board("target-089-continuum-hypothesis", "Continuum Hypothesis",
              board_status="independent")

W_FLT = _wiedijk("wiedijk-033-fermat-s-last-theorem", "Fermat's Last Theorem", 33)
W_PNT = _wiedijk("wiedijk-005-prime-number-theorem", "Prime Number Theorem", 5)
W_FTA = _wiedijk("wiedijk-002-fundamental-theorem-of-algebra",
                 "Fundamental Theorem of Algebra", 2,
                 status="partially-formalized")

BOARD = [B_MAGIC, B_RAMSEY, B_HODGE, B_GOLDBACH, B_LONELY, B_FLT, B_ABC, B_CH]
WIEDIJK = [W_FLT, W_PNT, W_FTA]


def _doc(counts=None):
    return build_nominations(BOARD, WIEDIJK, counts or {}, GEN_AT)


def _math_slugs(doc):
    return [n["slug"] for n in doc["mathematical_frontier"]]


# ------------------------------------------------------------ two frontiers

def test_two_frontiers_strictly_separated():
    doc = _doc()
    for n in doc["mathematical_frontier"]:
        assert n["seed_source"] == "targets-board"
        assert n["slug"].startswith("target-")
    for n in doc["formalization_frontier"]:
        assert n["seed_source"] == "wiedijk100"
        assert n["slug"].startswith("wiedijk-")
        # coverage framing, never open mathematics
        assert "coverage" in n["goal"]


def test_formalization_frontier_is_open_wiedijk_only():
    doc = _doc()
    slugs = {n["slug"] for n in doc["formalization_frontier"]}
    assert W_PNT["slug"] in slugs
    assert W_FTA["slug"] not in slugs  # partially-formalized => not open coverage gap


# ----------------------------------------------------- board_status exclusion

def test_resolved_disputed_independent_are_excluded_with_reason():
    doc = _doc()
    math = set(_math_slugs(doc))
    excluded = {e["slug"]: e for e in doc["excluded"]}
    for concept, status in [(B_FLT, "resolved"), (B_ABC, "disputed"),
                            (B_CH, "independent")]:
        assert concept["slug"] not in math
        assert concept["slug"] in excluded
        assert status in excluded[concept["slug"]]["reason"]


# ------------------------------------------------------------------- dedupe

def test_dedupe_excluded_board_winner_does_not_swallow_coverage_row():
    """Review blocker: FLT is PROVEN mathematics. Its board row wins the
    cross-seed dedupe but is then EXCLUDED (board_status=resolved) — the
    wiedijk coverage row must NOT vanish with it, or FLT lands on neither
    actionable list, violating the formalization frontier's own definition.
    The wiedijk row stays, annotated with the excluded duplicate it survived."""
    doc = _doc()
    by_slug = {n["slug"]: n for n in doc["formalization_frontier"]}
    row = by_slug[W_FLT["slug"]]  # KEPT, not dropped
    assert row["duplicate_of"] == B_FLT["slug"]
    assert "resolved" in row["note"]  # names why the board winner is excluded
    assert "coverage" in row["goal"]  # still coverage framing, never a campaign
    # The excluded board row still carries the annotation, saying the
    # duplicate was kept (never "not listed twice" — it IS listed).
    excluded = {e["slug"]: e for e in doc["excluded"]}
    dup = excluded[B_FLT["slug"]]["cross_seed_duplicate"]
    assert dup["slug"] == W_FLT["slug"]
    assert dup["seed_source"] == "wiedijk100"
    assert "kept" in dup["note"].lower()
    # Counts stay measured, and non-duplicate rows carry no annotation.
    assert doc["counts"]["formalization_frontier"] == \
        len(doc["formalization_frontier"])
    assert "duplicate_of" not in by_slug[W_PNT["slug"]]


def test_dedupe_annotates_nominated_row_when_math_row_is_open():
    board = [_board("target-999-prime-number-theorem", "Prime Number Theorem")]
    doc = build_nominations(board, [W_PNT], {}, GEN_AT)
    assert [n["slug"] for n in doc["formalization_frontier"]] == []
    nom = doc["mathematical_frontier"][0]
    assert nom["cross_seed_duplicate"]["slug"] == W_PNT["slug"]


def test_normalize_title_matches_across_punctuation():
    assert normalize_title("Fermat’s Last Theorem") == \
        normalize_title("Fermat's Last Theorem")


# --------------------------------------------------------------------- tiers

def test_engine_ready_only_from_curated_table_and_names_sub_statement():
    doc = _doc()
    by_slug = {n["slug"]: n for n in doc["mathematical_frontier"]}
    for slug, nom in by_slug.items():
        if nom["tier"] == "ENGINE-READY":
            assert slug in ENGINE_READY
            assert nom["sub_statement"].strip()  # the named finite sub-statement
        else:
            assert "sub_statement" not in nom
    assert by_slug[B_MAGIC["slug"]]["tier"] == "ENGINE-READY"
    assert by_slug[B_RAMSEY["slug"]]["tier"] == "ENGINE-READY"


def test_not_attackable_is_rendered_as_a_nomination_tier():
    doc = _doc()
    by_slug = {n["slug"]: n for n in doc["mathematical_frontier"]}
    assert by_slug[B_HODGE["slug"]]["tier"] == "NOT-ATTACKABLE-YET"
    assert by_slug[B_HODGE["slug"]]["evidence"]["tier_reason"]


def test_unmatched_concepts_default_to_formalize_first():
    doc = _doc()
    by_slug = {n["slug"]: n for n in doc["mathematical_frontier"]}
    assert by_slug[B_LONELY["slug"]]["tier"] == "FORMALIZE-FIRST"
    assert by_slug[B_GOLDBACH["slug"]]["tier"] == "FORMALIZE-FIRST"


def test_formalize_first_partially_formalized_ranks_above_open():
    doc = _doc()
    ff = [n for n in doc["mathematical_frontier"] if n["tier"] == "FORMALIZE-FIRST"]
    slugs = [n["slug"] for n in ff]
    assert slugs.index(B_GOLDBACH["slug"]) < slugs.index(B_LONELY["slug"])


def test_partially_formalized_cites_brockian_statement_module_as_evidence():
    doc = _doc()
    by_slug = {n["slug"]: n for n in doc["mathematical_frontier"]}
    ev = by_slug[B_GOLDBACH["slug"]]["evidence"]
    assert ev["brockian_statement_module"] == "Brockian.GoldbachComb"
    assert ev["atlas_status"] == "partially-formalized"
    assert "brockian_statement_module" not in by_slug[B_LONELY["slug"]]["evidence"]


def test_curated_tables_reference_real_board_slugs():
    seed = yaml.safe_load(
        (REPO / "concepts" / "targets-board.yaml").read_text())
    slugs = {c["slug"] for c in seed["concepts"]}
    assert set(ENGINE_READY) <= slugs
    assert set(NOT_ATTACKABLE) <= slugs
    for entry in ENGINE_READY.values():
        assert entry["sub_statement"].strip()
        assert entry["engine"].strip()


# ------------------------------------------------------------------ evidence

def test_every_nomination_carries_evidence():
    doc = _doc({B_MAGIC["slug"]: 2, W_PNT["slug"]: 1})
    for n in doc["mathematical_frontier"]:
        ev = n["evidence"]
        assert ev["seed_source"] == "targets-board"
        assert ev["board_status"] == "open"
        assert "alignment_count" in ev
        assert ev["tier_table"]["version"] >= 1
    by_slug = {n["slug"]: n for n in doc["mathematical_frontier"]}
    assert by_slug[B_MAGIC["slug"]]["evidence"]["alignment_count"] == 2
    assert by_slug[B_HODGE["slug"]]["evidence"]["alignment_count"] == 0


def test_count_noncandidate_excludes_candidate_tier():
    id_to_slug = {1: "a", 2: "b"}
    rows = [{"concept_id": 1, "tier": "CURATED"},
            {"concept_id": 1, "tier": "CANDIDATE"},
            {"concept_id": 2, "tier": "CANDIDATE"},
            {"concept_id": 3, "tier": "ALIGNED"}]  # unknown id ignored
    assert count_noncandidate(rows, id_to_slug) == {"a": 1}


# ----------------------------------------------------------------- document

def test_generated_at_is_injected_never_computed():
    doc = _doc()
    assert doc["generated_at"] == GEN_AT


def test_counts_are_measured_from_sections():
    doc = _doc()
    c = doc["counts"]
    assert c["mathematical_frontier"] == len(doc["mathematical_frontier"])
    assert c["formalization_frontier"] == len(doc["formalization_frontier"])
    assert c["excluded"] == len(doc["excluded"])
    tiers = c["tiers"]
    for tier in ("ENGINE-READY", "FORMALIZE-FIRST", "NOT-ATTACKABLE-YET"):
        assert tiers[tier] == sum(
            1 for n in doc["mathematical_frontier"] if n["tier"] == tier)


def test_generated_nominations_file_is_honest():
    """The committed artifact (produced by one real live-read run) must hold
    the line: measured counts, strict frontier separation, excluded section
    populated, ENGINE-READY always naming its sub-statement."""
    path = REPO / "concepts" / "frontier-nominations.yaml"
    assert path.exists(), "run tools/nominate_frontier.py to generate the artifact"
    doc = yaml.safe_load(path.read_text())
    assert doc["generated_at"]
    c = doc["counts"]
    assert c["mathematical_frontier"] == len(doc["mathematical_frontier"])
    assert c["formalization_frontier"] == len(doc["formalization_frontier"])
    assert c["excluded"] == len(doc["excluded"])
    seed = yaml.safe_load((REPO / "concepts" / "targets-board.yaml").read_text())
    board_slugs = {x["slug"] for x in seed["concepts"]}
    excluded_slugs = {e["slug"] for e in doc["excluded"]}
    for n in doc["mathematical_frontier"]:
        assert n["seed_source"] == "targets-board"
        assert n["slug"] in board_slugs
        assert n["slug"] not in excluded_slugs
        assert n["evidence"]["board_status"] not in {"resolved", "disputed",
                                                     "independent"}
        if n["tier"] == "ENGINE-READY":
            assert n["sub_statement"].strip()
    for n in doc["formalization_frontier"]:
        assert n["seed_source"] == "wiedijk100"
        assert "coverage" in n["goal"]


def test_document_roundtrips_through_yaml():
    doc = _doc()
    loaded = yaml.safe_load(yaml.safe_dump(doc, sort_keys=False,
                                           allow_unicode=True))
    assert loaded == doc
    assert loaded["generated_by"] == "tools/nominate_frontier.py"
    assert "never writes" in loaded["note"]

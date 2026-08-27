"""Tests for the candidate alignment proposer (pure logic — no network).

The live PostgREST verification pass runs only in the tool's __main__; here we
inject fixture-backed exists/search callables. All native names used in
fixtures are REAL set.mm labels (verified against the live atlas_statements
table on 2026-08-27) so the fixture mirrors upstream reality.
"""
import pathlib

import yaml

from tools.propose_candidates import (
    CURATED_KEYWORDS,
    build_document,
    name_similarity_candidates,
    propose,
)

REPO = pathlib.Path(__file__).resolve().parent.parent

# Real set.mm labels (subset), as present in the live metamath harvest.
FIXTURE_NAMES = frozenset(
    {"sqrt2irr", "sqrt2irr0", "canth", "canth2", "sbth", "bpos", "wilth",
     "1arith", "infpn", "prmunb", "pythag", "ballotth", "fta", "qnnen"}
)


def _exists(name):
    return name in FIXTURE_NAMES


def _search(prefix):
    return sorted(n for n in FIXTURE_NAMES if n.startswith(prefix))


def _no_search(prefix):
    return []


def _concept(num, slug, title):
    return {"slug": slug, "title": title, "wiedijk_number": num}


C_SQRT2 = _concept(1, "wiedijk-001-the-irrationality-of-the-square-root-of-2",
                   "The Irrationality of the Square Root of 2")
C_CANTOR = _concept(63, "wiedijk-063-cantor-s-theorem", "Cantor’s Theorem")
C_BERTRAND = _concept(98, "wiedijk-098-bertrand-s-postulate", "Bertrand’s Postulate")


def test_curated_proposal_is_candidate_with_evidence():
    props = propose([C_SQRT2], _exists, _no_search)
    assert len(props) == 1
    p = props[0]
    assert p["concept_slug"] == C_SQRT2["slug"]
    assert p["library"] == "metamath"
    assert p["native_name"] == "sqrt2irr"
    assert p["tier"] == "CANDIDATE"
    assert p["evidence"]["method"] == "keyword-heuristic"
    assert p["evidence"]["confidence"] in {"high", "medium", "low"}
    assert "sqrt2irr" in p["evidence"]["query"]


def test_unverified_names_are_never_emitted():
    props = propose([C_SQRT2, C_CANTOR, C_BERTRAND], lambda n: False, _no_search)
    assert props == []


def test_first_existing_curated_name_wins():
    keywords = {1: {"names": ["notarealset.mmlabel", "sqrt2irr"], "confidence": "high"}}
    props = propose([C_SQRT2], _exists, _no_search, keywords=keywords)
    assert [p["native_name"] for p in props] == ["sqrt2irr"]


def test_tier_is_always_candidate_never_curated_or_aligned():
    concepts = [C_SQRT2, C_CANTOR, C_BERTRAND]
    props = propose(concepts, _exists, _search)
    assert props
    assert {p["tier"] for p in props} == {"CANDIDATE"}


def test_name_similarity_fallback():
    # No curated entry -> the generic fallback searches by title tokens.
    props = propose([C_CANTOR], _exists, _search, keywords={})
    assert props
    p = props[0]
    assert p["native_name"] in {"canth", "canth2"}
    assert p["evidence"]["method"] == "name-similarity"
    assert p["evidence"]["confidence"] in {"medium", "low"}
    assert "ilike" in p["evidence"]["query"]


def test_name_similarity_candidates_are_ranked_and_capped():
    cands = name_similarity_candidates("Cantor’s Theorem", _search)
    assert 0 < len(cands) <= 2
    for name, query, confidence in cands:
        assert name in FIXTURE_NAMES
        assert confidence in {"medium", "low"}
        assert query.startswith("native_name=ilike.")


def test_max_proposals_cap_keeps_highest_confidence():
    concepts = [C_CANTOR, C_SQRT2, C_BERTRAND]
    keywords = {
        1: {"names": ["sqrt2irr"], "confidence": "high"},
        63: {"names": ["canth"], "confidence": "low"},
        98: {"names": ["bpos"], "confidence": "high"},
    }
    props = propose(concepts, _exists, _no_search, keywords=keywords, max_proposals=2)
    assert len(props) == 2
    assert {p["native_name"] for p in props} == {"sqrt2irr", "bpos"}


def test_one_proposal_per_concept_no_duplicates():
    props = propose([C_SQRT2, C_SQRT2], _exists, _search)
    keys = [(p["concept_slug"], p["native_name"]) for p in props]
    assert len(keys) == len(set(keys))


def test_build_document_shape_roundtrips():
    props = propose([C_SQRT2], _exists, _no_search)
    doc = build_document(props)
    dumped = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    loaded = yaml.safe_load(dumped)
    assert loaded["library"] == "metamath"
    assert loaded["proposal_count"] == len(props) == len(loaded["proposals"])
    assert loaded["generated_by"] == "tools/propose_candidates.py"
    assert "verified_against" in loaded


def test_curated_map_targets_real_wiedijk_numbers():
    seed = yaml.safe_load((REPO / "concepts" / "wiedijk100.yaml").read_text())
    numbers = {c["wiedijk_number"] for c in seed["concepts"]}
    assert set(CURATED_KEYWORDS) <= numbers
    for entry in CURATED_KEYWORDS.values():
        assert entry["names"], "curated entry with no names"
        assert entry["confidence"] in {"high", "medium", "low"}


def test_generated_candidates_file_is_honest():
    """The committed artifact (produced by one real run) must hold the line:
    CANDIDATE tier only, known slugs, evidence on every proposal."""
    path = REPO / "concepts" / "candidates-metamath.yaml"
    assert path.exists(), "run tools/propose_candidates.py to generate the artifact"
    doc = yaml.safe_load(path.read_text())
    seed = yaml.safe_load((REPO / "concepts" / "wiedijk100.yaml").read_text())
    slugs = {c["slug"] for c in seed["concepts"]}
    assert 20 <= doc["proposal_count"] <= 40
    assert doc["proposal_count"] == len(doc["proposals"])
    seen = set()
    for p in doc["proposals"]:
        assert p["tier"] == "CANDIDATE"
        assert p["library"] == "metamath"
        assert p["concept_slug"] in slugs
        assert p["evidence"]["method"] in {"keyword-heuristic", "name-similarity"}
        assert p["evidence"]["confidence"] in {"high", "medium", "low"}
        assert p["evidence"]["query"]
        key = (p["concept_slug"], p["native_name"])
        assert key not in seen
        seen.add(key)

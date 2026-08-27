import json
import pathlib

from harvesters.coq.harvest import _compare_versions, _parse_synopsis, harvest

FIX = pathlib.Path(__file__).parent / "fixtures" / "coq_opam_index_small.tar.gz"


def _rows(tmp_path):
    return [json.loads(l) for l in (tmp_path / "statements.jsonl").read_text().splitlines()]


def test_one_row_per_package_not_per_version(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    rows = _rows(tmp_path)
    # fixture holds 4 packages across 70 versioned opam files
    assert man["statement_count"] == len(rows) == 4
    assert {r["native_name"] for r in rows} == {
        "coq-subst", "coq-sail", "coq-equations", "coq-mathcomp-ssreflect"}


def test_row_shape(tmp_path):
    harvest(source=str(FIX), out_dir=tmp_path)
    for r in _rows(tmp_path):
        assert r["library"] == "coq"
        assert r["kind"] == "other"
        assert r["source_url"] == ("https://github.com/rocq-prover/opam/"
                                   f"tree/master/released/packages/{r['native_name']}")


def test_synopsis_of_latest_version_is_statement_text(tmp_path):
    harvest(source=str(FIX), out_dir=tmp_path)
    by_name = {r["native_name"]: r for r in _rows(tmp_path)}
    # coq-subst latest is 8.10.0 (numeric ordering: 8.10.0 > 8.9.0)
    assert by_name["coq-subst"]["statement_text"] == (
        "The confluence of Hardin-Lévy lambda-sigma-lift-calcul")
    # coq-equations latest is 1.3.1+9.0 (beats 1.3.1+8.20; 1.0~beta2 < 1.0)
    assert by_name["coq-equations"]["statement_text"] == (
        "Compatibility package, see rocq-equations")
    # coq-mathcomp-ssreflect latest is 2.6.0 (1.6 < 1.10.0 numerically)
    assert by_name["coq-mathcomp-ssreflect"]["statement_text"] == (
        "Compatibility package for rocq-mathcomp-ssreflect")
    # coq-sail uses the synopsis-on-next-line opam layout
    assert by_name["coq-sail"]["statement_text"] == (
        "Support library for Sail, a language for describing "
        "the instruction semantics of processors")


def test_source_version_comes_from_repo_stamp(tmp_path):
    man = harvest(source=str(FIX), out_dir=tmp_path)
    # the repo file inside the fixture carries: stamp: "2026-08-27 07:43"
    assert man["source_version"] == "2026-08-27 07:43"


def test_opam_version_ordering():
    assert _compare_versions("1.0~beta2", "1.0") < 0   # ~ sorts before everything
    assert _compare_versions("1.6", "1.10.0") < 0      # numeric, not lexicographic
    assert _compare_versions("1.3.1+8.20", "1.3.1+9.0") < 0
    assert _compare_versions("8.10.0", "8.9.0") > 0
    assert _compare_versions("0.20.2", "0.20.2") == 0


def test_parse_synopsis_missing_field_gives_none():
    assert _parse_synopsis('opam-version: "2.0"\nmaintainer: "x@y.z"\n') is None

"""End-to-end mini-pipeline: brockian fixture → harvest → plan_upsert.

Exercises the real seam between the harvest side (emit-validated jsonl on
disk) and the load side (pure planning), with a fake existing-names set in
place of the DB. No network, no monkeypatching — plan_upsert is pure.

The fixture registry holds 5 entries of which exactly 2 pass the inclusion
rule (PROVED + axioms_ok + sorry_free):
  Brockian.AbundantClosure.abundant_of_perfect_dvd
  Brockian.AbundantClosure.abundant_of_six_dvd
"""
import hashlib
import json
import pathlib

import pytest

from atlas.load import plan_upsert
from harvesters.brockian.harvest import harvest

FIX = pathlib.Path(__file__).parent / "fixtures" / "brockian_registry_small.json"

HARVESTED = {
    "Brockian.AbundantClosure.abundant_of_perfect_dvd",
    "Brockian.AbundantClosure.abundant_of_six_dvd",
}


def _run_pipeline(tmp_path):
    """Harvest the fixture, then re-read rows the way load() does —
    from the emitted statements.jsonl, not from in-memory state."""
    manifest = harvest(source=str(FIX), out_dir=tmp_path)
    blob = (tmp_path / "statements.jsonl").read_bytes()
    # Integrity check load() relies on implicitly: manifest describes the file.
    assert manifest["sha256"] == hashlib.sha256(blob).hexdigest()
    rows = [json.loads(l) for l in blob.decode("utf-8").splitlines() if l]
    assert manifest["statement_count"] == len(rows) == 2
    return rows


def test_pipeline_retires_vanished_upserts_all(tmp_path):
    rows = _run_pipeline(tmp_path)
    # Fake DB: one name still present upstream, one that vanished.
    existing = {
        "Brockian.AbundantClosure.abundant_of_perfect_dvd",
        "Brockian.Old.vanished_theorem",
    }
    plan = plan_upsert(existing, rows)
    assert plan["retire"] == {"Brockian.Old.vanished_theorem"}
    assert plan["upsert_count"] == 2


def test_pipeline_steady_state_retires_nothing(tmp_path):
    rows = _run_pipeline(tmp_path)
    plan = plan_upsert(HARVESTED, rows)
    assert plan["retire"] == set()
    assert plan["upsert_count"] == 2


def test_pipeline_first_harvest_into_empty_db(tmp_path):
    rows = _run_pipeline(tmp_path)
    plan = plan_upsert(set(), rows)
    assert plan["retire"] == set()
    assert plan["upsert_count"] == 2


def test_pipeline_big_shrink_trips_delta_gate(tmp_path):
    rows = _run_pipeline(tmp_path)
    # 10 live rows vs 2 harvested = 80% shrink: gate must refuse ...
    existing = HARVESTED | {f"Brockian.Old.thm_{i}" for i in range(8)}
    with pytest.raises(ValueError, match="delta"):
        plan_upsert(existing, rows)
    # ... and the explicit override must retire exactly the vanished 8.
    plan = plan_upsert(existing, rows, allow_big_delta=True)
    assert plan["retire"] == {f"Brockian.Old.thm_{i}" for i in range(8)}
    assert plan["upsert_count"] == 2

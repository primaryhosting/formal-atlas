import json
import pytest
import atlas.load as load_mod
from atlas.load import plan_upsert

def test_plan_upsert_computes_retired():
    existing = {"a", "b", "c"}
    harvested = [{"native_name": "a"}, {"native_name": "d"}]
    plan = plan_upsert(existing, harvested, allow_big_delta=True)
    assert plan["retire"] == {"b", "c"}
    assert plan["upsert_count"] == 2

def test_plan_upsert_empty_harvest_refuses():
    with pytest.raises(ValueError, match="refusing"):
        plan_upsert({"a"}, [])

def test_plan_upsert_big_delta_refuses_without_override():
    existing = {str(i) for i in range(100)}
    harvested = [{"native_name": str(i)} for i in range(70)]
    with pytest.raises(ValueError, match="delta"):
        plan_upsert(existing, harvested)
    assert plan_upsert(existing, harvested, allow_big_delta=True)["upsert_count"] == 70

def test_plan_upsert_first_harvest_allowed():
    assert plan_upsert(set(), [{"native_name": "a"}])["upsert_count"] == 1

def test_load_baseline_is_live_set_only(tmp_path, monkeypatch):
    """The existing-names baseline must exclude retired rows: an all-time
    baseline inflates the delta gate and re-retires the historical backlog.
    HTTP layer is monkeypatched — no network."""
    stmt = {"library": "brockian", "native_name": "a", "kind": "theorem",
            "source_url": "https://example.com/a"}
    (tmp_path / "statements.jsonl").write_text(json.dumps(stmt) + "\n")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "library": "brockian", "statement_count": 1,
        "harvested_at": "2026-08-26T00:00:00+00:00",
        "harvester_version": "0.1.0", "source_version": "v1"}))

    calls = {"get": [], "post": [], "patch": []}
    def fake_get_paged(url, key, path_query):
        calls["get"].append(path_query)
        return [{"native_name": "a"}]
    monkeypatch.setattr(load_mod, "get_paged", fake_get_paged)
    monkeypatch.setattr(load_mod, "post",
                        lambda *a, **k: calls["post"].append(a[2]))
    monkeypatch.setattr(load_mod, "patch",
                        lambda *a, **k: calls["patch"].append(a[2]))

    plan = load_mod.load(tmp_path, "https://x.supabase.co", "key")
    assert "retired=eq.false" in calls["get"][0]
    assert plan["retire"] == set()
    # exactly one harvest-run insert — the ok row (failure rows are the
    # workflow's job, never load()'s)
    assert len([p for p in calls["post"] if "harvest_runs" in p]) == 1

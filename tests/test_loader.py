import pytest
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

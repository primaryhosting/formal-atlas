"""Tests for concept-seed sync — module-prefix alignment resolution.

Spec (docs/2026-08-27-proving-flywheel-spec.md, stage 4): an alignment whose
native_name has no exact statement match is retried as a module reference —
declarations whose name starts with "<native_name>." or whose module equals
native_name — picking the lexicographically smallest name and recording
`resolution: module-prefix` in the evidence. The exact-match path is
byte-for-byte unchanged; no match stays ALIGNMENT PENDING. No network here:
the HTTP helpers are monkeypatched.
"""
import yaml

import concepts.sync_concepts as sync
from concepts.sync_concepts import pick_module_match


# ---------------------------------------------------------- pure resolution

def test_prefix_match_picks_lexicographically_smallest():
    rows = [
        {"id": 3, "native_name": "Brockian.GoldbachComb.zeta", "module": None},
        {"id": 1, "native_name": "Brockian.GoldbachComb.alpha", "module": None},
        {"id": 2, "native_name": "Brockian.GoldbachComb.beta", "module": None},
    ]
    assert pick_module_match("Brockian.GoldbachComb", rows)["id"] == 1


def test_module_column_match_counts():
    rows = [{"id": 7, "native_name": "goldbach_comb_lower",
             "module": "Brockian.GoldbachComb"}]
    assert pick_module_match("Brockian.GoldbachComb", rows)["id"] == 7


def test_no_match_returns_none():
    rows = [
        {"id": 1, "native_name": "Brockian.GoldbachCombinatorial.x", "module": None},
        {"id": 2, "native_name": "Brockian.Other.y", "module": "Brockian.Other"},
    ]
    assert pick_module_match("Brockian.GoldbachComb", rows) is None


def test_empty_candidates_returns_none():
    assert pick_module_match("Brockian.GoldbachComb", []) is None


# ----------------------------------------------------------- wiring (no net)

def _seed(tmp_path, native_name):
    doc = {
        "seed_source": "targets-board",
        "concepts": [{
            "slug": "target-008-goldbach-s-conjecture",
            "title": "Goldbach’s Conjecture",
            "status": "partially-formalized",
            "alignments": [{
                "library": "brockian",
                "native_name": native_name,
                "tier": "CURATED",
                "evidence": {"source": "riemannlab targets board"},
            }],
        }],
    }
    path = tmp_path / "seed.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    return path


def _patch(monkeypatch, statements_by_query):
    """Route get_paged by substring of the query; record post() calls."""
    posts = []

    def fake_get_paged(url, key, path_query):
        if path_query.startswith("atlas_concepts?"):
            return [{"id": 42}]
        for needle, rows in statements_by_query:
            if needle in path_query:
                return rows
        return []

    def fake_post(url, key, path_query, body, *, prefer=None):
        posts.append((path_query, body))

    monkeypatch.setattr(sync, "get_paged", fake_get_paged)
    monkeypatch.setattr(sync, "post", fake_post)
    return posts


def _alignment_posts(posts):
    return [(q, b) for q, b in posts if q.startswith("atlas_alignments")]


def test_exact_match_path_is_unchanged(monkeypatch, tmp_path):
    posts = _patch(monkeypatch, [
        ("native_name=eq.", [{"id": 9}]),
    ])
    synced, pending = sync.sync_file(_seed(tmp_path, "Brockian.GoldbachComb"),
                                     "http://x", "k")
    assert (synced, pending) == (1, 0)
    [(_, body)] = _alignment_posts(posts)
    row = body[0]
    assert row["statement_id"] == 9
    # evidence byte-for-byte what the seed carries — no resolution key
    assert row["evidence"] == {"source": "riemannlab targets board"}


def test_module_prefix_resolution_records_evidence(monkeypatch, tmp_path):
    posts = _patch(monkeypatch, [
        ("native_name=eq.", []),  # no exact match
        ("or=(", [
            {"id": 12, "native_name": "Brockian.GoldbachComb.two_le",
             "module": None},
            {"id": 11, "native_name": "Brockian.GoldbachComb.comb_lower",
             "module": None},
        ]),
    ])
    synced, pending = sync.sync_file(_seed(tmp_path, "Brockian.GoldbachComb"),
                                     "http://x", "k")
    assert (synced, pending) == (1, 0)
    [(_, body)] = _alignment_posts(posts)
    row = body[0]
    assert row["statement_id"] == 11  # lexicographically smallest name
    assert row["evidence"]["resolution"] == "module-prefix"
    assert row["evidence"]["resolved_declaration"] == "Brockian.GoldbachComb.comb_lower"
    assert row["evidence"]["source"] == "riemannlab targets board"  # kept


def test_non_seed_yaml_is_skipped_not_synced(monkeypatch, tmp_path, capsys):
    """concepts/ also holds non-seed YAMLs (candidate proposals, frontier
    nominations, campaign approvals) — sync must skip them, never crash or
    write."""
    posts = _patch(monkeypatch, [])
    path = tmp_path / "campaign-approvals.yaml"
    path.write_text(yaml.safe_dump({"approvals": []}), encoding="utf-8")
    assert sync.sync_file(path, "http://x", "k") == (0, 0)
    assert posts == []
    assert "not a concept seed, skipped" in capsys.readouterr().out


def test_unresolved_stays_alignment_pending(monkeypatch, tmp_path, capsys):
    posts = _patch(monkeypatch, [
        ("native_name=eq.", []),
        ("or=(", []),
    ])
    synced, pending = sync.sync_file(_seed(tmp_path, "Brockian.GoldbachComb"),
                                     "http://x", "k")
    assert (synced, pending) == (0, 1)
    assert _alignment_posts(posts) == []
    out = capsys.readouterr().out
    assert "ALIGNMENT PENDING: brockian/Brockian.GoldbachComb not harvested yet" in out

"""Property-style tests for atlas.emit.write_harvest.

No hypothesis dependency — deterministic seeded generation over a
unicode-heavy alphabet. Three properties:

  1. round-trip: the emitted statements.jsonl reparses to exactly the input
     statements (order-normalized — write_harvest sorts by native_name);
  2. sha256 stability: two writes of the same statement set (even shuffled)
     produce byte-identical statements.jsonl and identical manifest sha256,
     and the recorded sha256 really is the digest of the emitted file bytes;
  3. unicode-heavy names survive: CJK, Greek, combining marks, emoji,
     math-alphanumeric symbols — emitted with ensure_ascii=False, reparsed
     losslessly, and sorted deterministically.
"""
import hashlib
import json
import random

import pytest

from atlas.emit import write_harvest

# Codepoints deliberately spanning several planes and normalization traps.
_UNICODE_CHUNKS = [
    "α", "Ω", "λ", "ℝ", "ℵ₀", "∀x∈ℕ", "定理", "証明", "теорема",
    "e\u0301",     # 'e' + combining acute (NFD-style)
    "\u00e9",      # precomposed e-acute (NFC)
    "𝔽₂",               # math double-struck (astral plane)
    "🐍", "→", "⟨⟩", "ø", "ß",
]


def _gen_statements(n, seed):
    rng = random.Random(seed)
    stmts = []
    seen = set()
    for i in range(n):
        name = "".join(rng.choices(_UNICODE_CHUNKS, k=rng.randint(1, 4))) + f".{i}"
        assert name not in seen
        seen.add(name)
        s = {
            "library": "brockian",
            "native_name": name,
            "kind": rng.choice(["theorem", "definition", "axiom", "lemma",
                                "corollary", "other"]),
            "source_url": f"https://torus.riemannlab.com/explore/lean-registry?name={i}",
        }
        # Optional fields present-or-absent, including explicit nulls.
        if rng.random() < 0.7:
            s["statement_text"] = rng.choice(
                ["∀ n, n + 0 = n", "x ≤ y → f x ≤ f y", None, "π ≠ 22/7"])
        if rng.random() < 0.7:
            s["module"] = rng.choice(["Brockian.Ünïcode", "数学.部門", None])
        if rng.random() < 0.5:
            s["subject_codes"] = rng.sample(["11A25", "03B30", "05-XX"],
                                            rng.randint(0, 3))
        stmts.append(s)
    return stmts


def _reparse(out_dir):
    return [json.loads(l) for l in
            (out_dir / "statements.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_roundtrip_emitted_jsonl_reparses_to_input(tmp_path, seed):
    stmts = _gen_statements(40, seed)
    write_harvest(tmp_path, "brockian", stmts,
                  harvester_version="0.0.1", source_version="prop-test")
    parsed = _reparse(tmp_path)
    key = lambda s: s["native_name"]
    assert sorted(parsed, key=key) == sorted(stmts, key=key)


@pytest.mark.parametrize("seed", [0, 7])
def test_sha256_stable_across_writes_and_shuffles(tmp_path, seed):
    stmts = _gen_statements(30, seed)
    shuffled = list(stmts)
    random.Random(seed + 999).shuffle(shuffled)
    man_a = write_harvest(tmp_path / "a", "brockian", stmts,
                          harvester_version="0.0.1", source_version="v")
    man_b = write_harvest(tmp_path / "b", "brockian", shuffled,
                          harvester_version="0.0.1", source_version="v")
    blob_a = (tmp_path / "a" / "statements.jsonl").read_bytes()
    blob_b = (tmp_path / "b" / "statements.jsonl").read_bytes()
    assert blob_a == blob_b
    assert man_a["sha256"] == man_b["sha256"]
    # The manifest sha256 is a real digest of the emitted file bytes.
    assert man_a["sha256"] == hashlib.sha256(blob_a).hexdigest()


def test_unicode_names_survive_verbatim(tmp_path):
    names = ["定理.完全数", "θεώρημα.Ω", "e\u0301clat", "\u00e9clat",
             "𝔽₂.linear", "🐍.serpent", "ℵ₀≤𝔠"]
    stmts = [{"library": "brockian", "native_name": n, "kind": "theorem",
              "source_url": "https://torus.riemannlab.com/x"} for n in names]
    write_harvest(tmp_path, "brockian", stmts,
                  harvester_version="0.0.1", source_version="v")
    raw = (tmp_path / "statements.jsonl").read_text(encoding="utf-8")
    # ensure_ascii=False — the actual characters, never \uXXXX escapes.
    assert "定理" in raw and "🐍" in raw
    assert "\\u" not in raw
    parsed = _reparse(tmp_path)
    # Lossless: NFC "éclat" and NFD "éclat" both survive, distinct.
    assert {p["native_name"] for p in parsed} == set(names)
    # Deterministic order: codepoint sort by native_name.
    assert [p["native_name"] for p in parsed] == sorted(names)


def test_manifest_statement_count_matches_file(tmp_path):
    stmts = _gen_statements(17, seed=3)
    man = write_harvest(tmp_path, "brockian", stmts,
                        harvester_version="0.0.1", source_version="v")
    assert man["statement_count"] == 17 == len(_reparse(tmp_path))

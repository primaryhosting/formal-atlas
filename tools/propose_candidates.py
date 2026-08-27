"""Propose CANDIDATE alignments: Wiedijk-100 concepts -> metamath statements.

The novel core of the atlas, first cut. For each concept in
concepts/wiedijk100.yaml, propose set.mm labels that plausibly formalize it,
by two methods:

  keyword-heuristic  — a curated map keyed by Wiedijk number, drawn from
                       Metamath's own "Formalizing 100 Theorems" page
                       (https://us.metamath.org/mm_100.html) where we are
                       confident of the label. Confidence reflects curator
                       certainty about the label, NOT proof of alignment.
  name-similarity    — generic fallback for unmapped concepts: prefix-search
                       live native_names by title tokens, score by token
                       overlap. Always medium/low confidence.

Honesty rules baked in:
  * every emitted native_name is verified to EXIST in the live
    atlas_statements table (library_id=metamath) before emission — a curated
    guess that is not a real set.mm label is silently dropped;
  * tier is always CANDIDATE — existence of a plausibly-named statement is
    NOT alignment; promotion to ALIGNED/CURATED is a human curation act;
  * output is capped at MAX_PROPOSALS (quality over quantity), keeping the
    highest-confidence proposals first.

The pure matching logic (propose / name_similarity_candidates /
build_document) is unit-tested with fixtures; only __main__ touches the
network (read-only GETs with the PUBLIC anon key, which is published in the
site bundle — not a secret).
"""
import argparse
import datetime as _dt
import pathlib
import re

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent

SUPABASE_URL = "https://ocketgwbdzpxfjjkbfyb.supabase.co"
STATEMENTS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/atlas_statements"
# Public anon key (published in the site bundle; read-only under RLS).
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ja2V0Z3diZHpweGZqamtiZnliIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3NjQ1MjE5ODgsImV4cCI6MjA4MDA5Nzk4OH0."
    "SZXkEbfc6MtwF7g7iWBQIwrH6C5kxEIeVCUqVsfJSII"
)

LIBRARY = "metamath"
MAX_PROPOSALS = 40

# Curated label guesses keyed by Wiedijk number, pruned deliberately to the
# 38 entries the curator is most confident of, so the emitted set (cap 40,
# incl. fallback) is a curation choice rather than blind truncation. Source:
# Metamath's own "Formalizing 100 Theorems" page
# (https://us.metamath.org/mm_100.html) as recalled by the curator — recall
# can be wrong, hence every name is re-verified against the live table before
# emission and dropped if absent. Order within `names` = preference; the
# first name that exists in the live table wins for that concept.
CURATED_KEYWORDS = {
    1:  {"names": ["sqrt2irr", "sqrt2irr0"], "confidence": "high"},
    2:  {"names": ["fta"], "confidence": "high"},
    3:  {"names": ["qnnen"], "confidence": "high"},
    4:  {"names": ["pythag"], "confidence": "high"},
    5:  {"names": ["pnt"], "confidence": "high"},
    7:  {"names": ["lgsquad"], "confidence": "high"},
    9:  {"names": ["areacirc"], "confidence": "high"},
    10: {"names": ["eulerth"], "confidence": "high"},
    11: {"names": ["infpn", "prmunb"], "confidence": "high"},
    14: {"names": ["basel"], "confidence": "high"},
    15: {"names": ["ftc1", "ftc2"], "confidence": "high"},
    17: {"names": ["demoivre"], "confidence": "high"},
    18: {"names": ["aaliou"], "confidence": "high"},
    19: {"names": ["4sq"], "confidence": "high"},
    20: {"names": ["2sq"], "confidence": "high"},
    22: {"names": ["ruc", "rucALT"], "confidence": "high"},
    23: {"names": ["pythagtrip"], "confidence": "high"},
    25: {"names": ["sbth"], "confidence": "high"},
    30: {"names": ["ballotth"], "confidence": "high"},
    31: {"names": ["ramsey"], "confidence": "high"},
    35: {"names": ["taylth"], "confidence": "high"},
    38: {"names": ["amgm"], "confidence": "high"},
    44: {"names": ["binom"], "confidence": "high"},
    48: {"names": ["dirith"], "confidence": "high"},
    51: {"names": ["wilth"], "confidence": "high"},
    54: {"names": ["konigsberg"], "confidence": "high"},
    57: {"names": ["heron"], "confidence": "high"},
    60: {"names": ["bezout"], "confidence": "high"},
    63: {"names": ["canth", "canth2"], "confidence": "high"},
    64: {"names": ["lhop"], "confidence": "high"},
    74: {"names": ["nnind"], "confidence": "high"},
    75: {"names": ["mvth"], "confidence": "high"},
    79: {"names": ["ivth"], "confidence": "high"},
    80: {"names": ["1arith"], "confidence": "high"},
    81: {"names": ["prmrec"], "confidence": "high"},
    90: {"names": ["stirling"], "confidence": "high"},
    96: {"names": ["incexc"], "confidence": "high"},
    98: {"names": ["bpos"], "confidence": "high"},
}

# Words that carry no signal for matching set.mm labels.
_STOPWORDS = frozenset(
    "the of a an and or for in to is are all every there s t "
    "theorem theorems lemma formula problem principle rule law laws "
    "number numbers general solution solutions".split()
)

_CONF_ORDER = {"high": 0, "medium": 1, "low": 2}


def _title_tokens(title):
    tokens = re.split(r"[^a-z0-9]+", title.lower())
    return [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]


def name_similarity_candidates(title, search):
    """Generic fallback: prefix-search live names by title tokens.

    `search(prefix)` returns native names starting with `prefix` (fixture
    lists in tests; live ilike queries in __main__). Returns up to 2
    (name, query, confidence) tuples, best first.
    """
    tokens = _title_tokens(title)
    scored = {}
    for tok in tokens:
        prefix = tok[:4]
        for name in search(prefix):
            matched = sum(1 for t in tokens if t[:4] in name)
            query = f"native_name=ilike.{prefix}*"
            prev = scored.get(name)
            if prev is None or matched > prev[0]:
                scored[name] = (matched, query)
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1][0], len(kv[0]), kv[0]))
    out = []
    for name, (matched, query) in ranked[:2]:
        confidence = "medium" if matched >= 2 else "low"
        out.append((name, query, confidence))
    return out


def _proposal(slug, name, method, query, confidence):
    return {
        "concept_slug": slug,
        "library": LIBRARY,
        "native_name": name,
        "tier": "CANDIDATE",  # by definition; never CURATED/ALIGNED here
        "evidence": {"method": method, "query": query, "confidence": confidence},
    }


def propose(concepts, exists, search, *, keywords=None, max_proposals=MAX_PROPOSALS):
    """Pure proposer. `exists(name)` and `search(prefix)` are injected so
    tests run against fixtures; __main__ wires them to the live table.

    One proposal per concept (first verified curated name, else best
    name-similarity hits); output capped at `max_proposals`, keeping the
    highest-confidence proposals (stable within a confidence band).
    """
    if keywords is None:
        keywords = CURATED_KEYWORDS
    proposals = []
    seen = set()
    for concept in concepts:
        slug = concept["slug"]
        entry = keywords.get(concept.get("wiedijk_number"))
        matched = False
        if entry:
            for name in entry["names"]:
                if exists(name):
                    key = (slug, name)
                    if key not in seen:
                        seen.add(key)
                        proposals.append(_proposal(
                            slug, name, "keyword-heuristic",
                            f"native_name=eq.{name}", entry["confidence"]))
                    matched = True
                    break
        if not matched:
            for name, query, confidence in name_similarity_candidates(
                    concept.get("title", ""), search):
                key = (slug, name)
                if key not in seen:
                    seen.add(key)
                    proposals.append(_proposal(
                        slug, name, "name-similarity", query, confidence))
    proposals.sort(key=lambda p: _CONF_ORDER[p["evidence"]["confidence"]])
    return proposals[:max_proposals]


def build_document(proposals):
    return {
        "generated_by": "tools/propose_candidates.py",
        "library": LIBRARY,
        "seed_source": "concepts/wiedijk100.yaml",
        "verified_against": (
            f"{STATEMENTS_ENDPOINT} (library_id={LIBRARY}; every native_name "
            "confirmed present at generation time)"
        ),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "note": (
            "CANDIDATE proposals only — plausible name matches, NOT verified "
            "alignments. Never count these in headline numbers."
        ),
        "proposal_count": len(proposals),
        "proposals": proposals,
    }


# ---------------------------------------------------------------------------
# Live PostgREST access (main-path only; unit tests never reach this code).
# ---------------------------------------------------------------------------

def _live_session():
    import requests

    s = requests.Session()
    s.headers.update({"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"})
    return s


def _fetch_existing(session, names, chunk=80):
    """Return the subset of `names` present in the live metamath harvest."""
    names = sorted(set(names))
    found = set()
    for i in range(0, len(names), chunk):
        batch = names[i:i + chunk]
        resp = session.get(
            STATEMENTS_ENDPOINT,
            params={
                "library_id": f"eq.{LIBRARY}",
                "native_name": f"in.({','.join(batch)})",
                "select": "native_name",
            },
            timeout=30,
        )
        resp.raise_for_status()
        found.update(row["native_name"] for row in resp.json())
    return found


def _live_search(session, prefix, limit=25, _cache={}):
    """Prefix search over live metamath names. Cached per prefix; a failed
    search degrades to [] with a warning (fewer fallback proposals — honest
    about it — rather than a crashed run)."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", prefix):
        return []
    if prefix in _cache:
        return _cache[prefix]
    try:
        resp = session.get(
            STATEMENTS_ENDPOINT,
            params={
                "library_id": f"eq.{LIBRARY}",
                "native_name": f"ilike.{prefix}*",
                "select": "native_name",
                "limit": str(limit),
            },
            timeout=30,
        )
        resp.raise_for_status()
        names = [row["native_name"] for row in resp.json()]
    except Exception as exc:  # noqa: BLE001 — degrade, don't crash the run
        print(f"warning: search {prefix!r} failed ({exc}); treating as no hits")
        names = []
    _cache[prefix] = names
    return names


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--concepts", default=str(REPO / "concepts" / "wiedijk100.yaml"))
    ap.add_argument("--out", default=str(REPO / "concepts" / "candidates-metamath.yaml"))
    ap.add_argument("--max-proposals", type=int, default=MAX_PROPOSALS)
    args = ap.parse_args(argv)

    concepts = yaml.safe_load(pathlib.Path(args.concepts).read_text())["concepts"]
    session = _live_session()

    curated_names = [n for e in CURATED_KEYWORDS.values() for n in e["names"]]
    existing = _fetch_existing(session, curated_names)
    dropped = sorted(set(curated_names) - existing)

    proposals = propose(
        concepts,
        existing.__contains__,
        lambda prefix: _live_search(session, prefix),
        max_proposals=args.max_proposals,
    )
    # Belt-and-braces: re-verify every emitted name (covers the fallback path
    # too, cheaply) so nothing unverified can reach the artifact.
    final_names = _fetch_existing(session, [p["native_name"] for p in proposals])
    proposals = [p for p in proposals if p["native_name"] in final_names]

    doc = build_document(proposals)
    out = pathlib.Path(args.out)
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
                   encoding="utf-8", newline="")

    by_conf = {}
    by_method = {}
    for p in proposals:
        by_conf[p["evidence"]["confidence"]] = by_conf.get(p["evidence"]["confidence"], 0) + 1
        by_method[p["evidence"]["method"]] = by_method.get(p["evidence"]["method"], 0) + 1
    print(f"wrote {out} — {len(proposals)} proposals "
          f"(confidence {by_conf}, method {by_method})")
    if dropped:
        print(f"curated guesses NOT in live table (dropped): {', '.join(dropped)}")


if __name__ == "__main__":
    main()

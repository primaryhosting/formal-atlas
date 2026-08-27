"""Nominate frontier concepts for proving campaigns — flywheel stage 1.

Spec: docs/2026-08-27-proving-flywheel-spec.md. Reads the two concept seeds
and the live alignment table, and emits concepts/frontier-nominations.yaml —
a PROPOSAL DOCUMENT for the Chris gate. This tool never writes to the
database; approvals live separately in concepts/campaign-approvals.yaml.

Two frontiers, never mixed:

  mathematical    — seed_source targets-board: genuinely open problems. A
                    campaign means progress on a NAMED certifiable
                    sub-statement, tiered by the curated tables below
                    (curation-as-code: versioned, reviewed in git, no LLM).
  formalization   — seed_source wiedijk100, status open: PROVEN mathematics
                    the Atlas has not yet recorded a verification for.
                    Coverage work, never open mathematics.

Honesty rules baked in:
  * measured numbers only, stamped with an EXPLICIT generation date (CLI arg
    or ATLAS_GENERATED_AT env — never computed inside the logic);
  * live alignment counts exclude CANDIDATE tier — plausible name matches are
    never nomination evidence;
  * board problems whose board_status is resolved/disputed/independent are
    never nominated: they land in an explicit `excluded:` section with the
    reason;
  * cross-seed duplicates (e.g. Fermat's Last Theorem on both seeds) are
    deduped by normalized title — the mathematical row wins and the duplicate
    is annotated, not listed twice;
  * ENGINE-READY requires a named finite sub-statement in the curated table;
    NOT-ATTACKABLE-YET is rendered as prominently as the other tiers.

The pure logic (classify / dedupe / build_nominations) is unit-tested with
fixtures; only __main__ touches the network (read-only GETs through the
atlas.load HTTP layer with the PUBLIC anon key, which is published in the
site bundle — not a secret; the tools/propose_candidates.py precedent).
"""
import argparse
import os
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent

SUPABASE_URL = "https://ocketgwbdzpxfjjkbfyb.supabase.co"
# Public anon key (published in the site bundle; read-only under RLS) — same
# constant as tools/propose_candidates.py.
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ja2V0Z3diZHpweGZqamtiZnliIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3NjQ1MjE5ODgsImV4cCI6MjA4MDA5Nzk4OH0."
    "SZXkEbfc6MtwF7g7iWBQIwrH6C5kxEIeVCUqVsfJSII"
)

MATH_SEED = "targets-board"
FORM_SEED = "wiedijk100"
EXCLUDED_BOARD_STATUSES = ("resolved", "disputed", "independent")

# --------------------------------------------------------- curated tier tables
#
# Curation-as-code: reviewed in git, versioned, no LLM. Bump the version on
# any table change so every emitted document names the table that classified
# it. ENGINE-READY entries MUST name the finite sub-statement an engine can
# certify — an unbounded "infinitely many X" concept is NOT engine-ready
# merely because instances are searchable. When in doubt a concept stays in
# FORMALIZE-FIRST or NOT-ATTACKABLE-YET (conservative beats impressive).
TIER_TABLE_VERSION = 1

ENGINE_READY = {
    "target-098-3-3-magic-square-of-squares": {
        "sub_statement": (
            "No 3×3 magic square of nine distinct perfect squares exists "
            "with all entries ≤ B² for an explicitly stated bound B: an "
            "exhaustive bounded search over the parametrized candidate "
            "families, emitting a machine-checkable certificate of "
            "exhaustion for that bound. The bound is part of the claim."
        ),
        "engine": "bounded exhaustive search (AutoLab-driven solver)",
        "certificate": "search-exhaustion trace checked by an independent verifier",
    },
    "target-084-ramsey-number-r-5-5": {
        "sub_statement": (
            "Bound work on R(5,5) (known window [43,46]): an UNSAT "
            "certificate (DRAT or equivalent) for an explicit SAT encoding "
            "of a monochromatic-K5-free 2-coloring of K_n at a stated n — "
            "the certified statement is the unsatisfiability of that "
            "encoding, nothing more."
        ),
        "engine": "SAT solver with proof logging",
        "certificate": "DRAT/LRAT proof checked by a verified checker",
    },
    "target-097-perfect-cuboid-euler-brick": {
        "sub_statement": (
            "No perfect cuboid exists with smallest edge ≤ B for an "
            "explicitly stated bound B: exhaustive search over the bounded "
            "parameter space emitting a certificate of exhaustion. The "
            "bound is part of the claim."
        ),
        "engine": "bounded exhaustive search (AutoLab-driven solver)",
        "certificate": "search-exhaustion trace checked by an independent verifier",
    },
    "target-020-brocard-s-problem": {
        "sub_statement": (
            "The only n ≤ B with n! + 1 a perfect square are n ∈ {4, 5, 7}, "
            "for an explicitly stated bound B: a per-n bounded verification "
            "whose certificate is the checkable computation trace. The "
            "bound is part of the claim."
        ),
        "engine": "bounded verification (Brockian pipeline or AutoLab-driven solver)",
        "certificate": "per-n verification trace checked by an independent verifier",
    },
}

NOT_ATTACKABLE = {
    "target-003-hodge-conjecture": (
        "beyond current engines: no certifiable finite sub-statement and no "
        "settled formal-statement path in current libraries"
    ),
    "target-004-navier-stokes-existence-smoothness": (
        "beyond current engines: the analytic setting (3D PDE "
        "existence/smoothness) has no certifiable finite sub-statement and "
        "no settled formal-statement path in current libraries"
    ),
    "target-005-yang-mills-existence-mass-gap": (
        "beyond current engines: no agreed-upon rigorous formal statement "
        "exists to formalize, let alone a certifiable finite sub-statement"
    ),
}

_TIER_ORDER = {"ENGINE-READY": 0, "FORMALIZE-FIRST": 1, "NOT-ATTACKABLE-YET": 2}


# ------------------------------------------------------------------ pure logic

def normalize_title(title):
    """Dedupe key: lowercase, punctuation-insensitive (curly vs straight
    apostrophes, dashes, ×, etc. all collapse)."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def count_noncandidate(alignment_rows, id_to_slug):
    """Live alignment counts per concept slug, CANDIDATE tier excluded —
    plausible name matches are never nomination evidence. Rows whose
    concept_id is unknown are ignored (concept outside the tracked seeds)."""
    counts = {}
    for row in alignment_rows:
        if row["tier"] == "CANDIDATE":
            continue
        slug = id_to_slug.get(row["concept_id"])
        if slug is not None:
            counts[slug] = counts.get(slug, 0) + 1
    return counts


def classify(slug, *, engine_ready=None, not_attackable=None):
    """Tier a mathematical-frontier concept via the curated tables.

    Returns (tier, table_entry_or_None, reason). Anything not explicitly
    tabled defaults to FORMALIZE-FIRST — the first certifiable move for an
    open problem is a precise formal statement, which claims nothing about
    provability.
    """
    engine_ready = ENGINE_READY if engine_ready is None else engine_ready
    not_attackable = NOT_ATTACKABLE if not_attackable is None else not_attackable
    if slug in engine_ready:
        return ("ENGINE-READY", engine_ready[slug],
                "curated table names a certifiable finite sub-statement")
    if slug in not_attackable:
        return "NOT-ATTACKABLE-YET", None, not_attackable[slug]
    return ("FORMALIZE-FIRST", None,
            "first certifiable move is a precise formal statement "
            "(default tier — not in either curated table)")


def _duplicate_annotation(wiedijk_concept, *, kept=False):
    if kept:
        note = ("same concept by normalized title; this board row is "
                "excluded (not open frontier), so the wiedijk row is kept "
                "on the formalization frontier — proven mathematics without "
                "a recorded verification is still a coverage target")
    else:
        note = ("same concept by normalized title; the mathematical-frontier "
                "row wins — annotated here, not listed twice")
    return {
        "slug": wiedijk_concept["slug"],
        "seed_source": FORM_SEED,
        "note": note,
    }


def build_nominations(board_concepts, wiedijk_concepts, alignment_counts,
                      generated_at, *, engine_ready=None, not_attackable=None):
    """Pure builder: seeds + injected live alignment counts + explicit
    generation date -> the nominations document. No I/O, no clock."""
    # Cross-seed dedupe map: normalized board title -> board slug.
    board_by_title = {normalize_title(c["title"]): c["slug"]
                      for c in board_concepts}
    # Board rows the loop below will EXCLUDE (resolved/disputed/independent).
    # The dedupe must know this up front: when the winning board row is
    # excluded, dropping the wiedijk duplicate would strand the concept on
    # NEITHER actionable list — e.g. Fermat's Last Theorem, proven
    # mathematics, is exactly what the formalization frontier is FOR.
    excluded_board = {c["slug"]: c.get("board_status") for c in board_concepts
                      if c.get("board_status") in EXCLUDED_BOARD_STATUSES}
    duplicates = {}  # board slug -> wiedijk duplicate annotation
    formalization = []
    for c in wiedijk_concepts:
        if c.get("status", "open") != "open":
            continue  # coverage frontier = no recorded verification yet
        board_slug = board_by_title.get(normalize_title(c["title"]))
        if board_slug is not None:
            kept = board_slug in excluded_board
            duplicates[board_slug] = _duplicate_annotation(c, kept=kept)
            if not kept:
                continue  # mathematical row wins; annotated, not listed twice
            # The winning board row is excluded — keep the coverage row.
        entry = {
            "slug": c["slug"],
            "title": c["title"],
            "seed_source": FORM_SEED,
            "wiedijk_number": c.get("wiedijk_number"),
            "goal": ("coverage — find or produce a recorded formalization of "
                     "this PROVEN theorem; never a campaign to prove it"),
            "evidence": {
                "seed_source": FORM_SEED,
                "atlas_status": "open",
                "alignment_count": alignment_counts.get(c["slug"], 0),
            },
        }
        if board_slug is not None:
            entry["duplicate_of"] = board_slug
            entry["note"] = (
                f"cross-seed duplicate of {board_slug}, whose board row is "
                f"excluded (board_status={excluded_board[board_slug]}) — "
                "kept here because a proven theorem without a recorded "
                "formalization is a coverage target by definition")
        formalization.append(entry)

    nominations = []
    excluded = []
    for c in board_concepts:
        slug = c["slug"]
        board_status = c.get("board_status")
        if board_status in EXCLUDED_BOARD_STATUSES:
            entry = {
                "slug": slug,
                "title": c["title"],
                "board_status": board_status,
                "reason": (f"board_status={board_status} — never nominated "
                           "(resolved/disputed/independent problems are not "
                           "open frontier)"),
            }
            if slug in duplicates:
                entry["cross_seed_duplicate"] = duplicates[slug]
            excluded.append(entry)
            continue
        tier, table_entry, reason = classify(
            slug, engine_ready=engine_ready, not_attackable=not_attackable)
        status = c.get("status", "open")
        evidence = {
            "seed_source": MATH_SEED,
            "board_status": board_status,
            "atlas_status": status,
            "alignment_count": alignment_counts.get(slug, 0),
            "tier_table": {"version": TIER_TABLE_VERSION,
                           "matched": slug if table_entry or tier ==
                           "NOT-ATTACKABLE-YET" else "default"},
            "tier_reason": reason,
        }
        brockian = [a["native_name"] for a in c.get("alignments") or []
                    if a.get("library") == "brockian"]
        if brockian:
            evidence["brockian_statement_module"] = brockian[0]
        nom = {
            "slug": slug,
            "title": c["title"],
            "seed_source": MATH_SEED,
            "tier": tier,
        }
        if table_entry:
            nom["sub_statement"] = table_entry["sub_statement"]
            nom["engine"] = table_entry["engine"]
            nom["certificate"] = table_entry["certificate"]
        nom["evidence"] = evidence
        if slug in duplicates:
            nom["cross_seed_duplicate"] = duplicates[slug]
        nominations.append(nom)

    # Rank: tier first; inside FORMALIZE-FIRST, partially-formalized (its
    # first certifiable move is already done) above open; then slug for
    # determinism.
    def _rank(n):
        status_rank = 0 if n["evidence"]["atlas_status"] == "partially-formalized" else 1
        return (_TIER_ORDER[n["tier"]], status_rank, n["slug"])

    nominations.sort(key=_rank)

    tier_counts = {t: sum(1 for n in nominations if n["tier"] == t)
                   for t in _TIER_ORDER}
    return {
        "generated_by": "tools/nominate_frontier.py",
        "generated_at": generated_at,
        "spec": "docs/2026-08-27-proving-flywheel-spec.md",
        "tier_table_version": TIER_TABLE_VERSION,
        "note": (
            "Proposal document only — this tool never writes to the database. "
            "Nothing here is approved: approvals are hand-recorded in "
            "concepts/campaign-approvals.yaml (the Chris gate). Alignment "
            "counts are live measurements with CANDIDATE tier excluded."
        ),
        "counts": {
            "mathematical_frontier": len(nominations),
            "formalization_frontier": len(formalization),
            "excluded": len(excluded),
            "cross_seed_duplicates": len(duplicates),
            "tiers": tier_counts,
        },
        "mathematical_frontier": nominations,
        "formalization_frontier": formalization,
        "excluded": excluded,
    }


# ---------------------------------------------------------------------------
# Live PostgREST access (main-path only; unit tests never reach this code).
# Read-only GETs through the atlas.load HTTP layer with the public anon key.
# ---------------------------------------------------------------------------

def _fetch_alignment_counts():
    sys.path.insert(0, str(REPO))
    from atlas.load import get_paged

    concept_rows = get_paged(SUPABASE_URL, ANON_KEY,
                             "atlas_concepts?select=id,slug&order=id")
    id_to_slug = {r["id"]: r["slug"] for r in concept_rows}
    alignment_rows = get_paged(SUPABASE_URL, ANON_KEY,
                               "atlas_alignments?select=concept_id,tier&order=id")
    return count_noncandidate(alignment_rows, id_to_slug)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--board", default=str(REPO / "concepts" / "targets-board.yaml"))
    ap.add_argument("--wiedijk", default=str(REPO / "concepts" / "wiedijk100.yaml"))
    ap.add_argument("--out", default=str(REPO / "concepts" / "frontier-nominations.yaml"))
    ap.add_argument("--generated-at",
                    default=os.environ.get("ATLAS_GENERATED_AT"),
                    help="explicit generation timestamp (or ATLAS_GENERATED_AT "
                         "env); defaults to now, computed HERE, never inside "
                         "the logic")
    args = ap.parse_args(argv)

    generated_at = args.generated_at
    if not generated_at:
        import datetime as _dt  # main-path only — the logic never sees a clock
        generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()

    board = yaml.safe_load(pathlib.Path(args.board).read_text())["concepts"]
    wiedijk = yaml.safe_load(pathlib.Path(args.wiedijk).read_text())["concepts"]
    alignment_counts = _fetch_alignment_counts()  # live, CANDIDATE excluded

    doc = build_nominations(board, wiedijk, alignment_counts, generated_at)
    out = pathlib.Path(args.out)
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
                   encoding="utf-8", newline="")
    c = doc["counts"]
    print(f"wrote {out} — mathematical {c['mathematical_frontier']} "
          f"(tiers {c['tiers']}), formalization {c['formalization_frontier']}, "
          f"excluded {c['excluded']}, duplicates {c['cross_seed_duplicates']}")


if __name__ == "__main__":
    main()

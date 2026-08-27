# The Proving Flywheel — design spec

*2026-08-27 · status: REVIEWED (adversarial pass, 11 issues fixed) · owner:
Christopher Brock / Riemann Labs*

## The one-sentence idea

Close the loop between what the Atlas records as unproven-or-unformalized and
the engines that produce certificates: **frontier → nomination → (Chris gate)
→ campaign → certificate landing in the registry → harvest → CURATED alignment
in the Atlas.**

Every segment exists except two: nothing nominates, and the alignment step
does not close at module granularity. This spec builds both and nothing else.

## Two frontiers, not one

The concept index carries two seeds with different frontier meanings; the
nominator MUST NOT mix them:

- **Mathematical frontier** (`seed_source: targets-board`): genuinely open
  problems. The goal of a campaign is mathematical progress on a named,
  certifiable sub-statement.
- **Formalization frontier** (`seed_source: wiedijk100`, status `open` —
  measured 22 today): *proven* mathematics the Atlas has not yet recorded a
  verification for. The goal is coverage (find/produce the formalization),
  never "proving FTA."

Cross-seed duplicates exist (e.g. Fermat's Last Theorem appears as
`wiedijk-033-…` and `target-036-…`). The nominator dedupes by normalized
title; the mathematical-frontier row wins and the duplicate is annotated, not
listed twice.

## Loop stages

### 1. Nominate — deterministic, read-only, runs every edition

`tools/nominate_frontier.py`:

- **Reads** live concepts + alignments via the existing `atlas.load` HTTP layer
  (requests + the published anon key, Range pagination — the
  `tools/propose_candidates.py` precedent). Tests are fixture-only, no network.
- **Joins the in-repo `concepts/targets-board.yaml`** for `board_status`
  (the DB does not carry it): concepts whose board_status is `resolved`,
  `disputed`, or `independent` are excluded from nomination and listed in an
  explicit `excluded:` section with the reason.
- **Classifies** the mathematical frontier into attackability tiers via a
  versioned, table-driven map (curation-as-code; reviewed in git; no LLM):

| Tier | Meaning |
|------|---------|
| `ENGINE-READY` | An engine can certify a **named finite sub-statement**, and the nomination names it (e.g. target-098 magic square of squares: exhaustive bounded search emits a certificate for a stated bound; target-084 R(5,5): SAT-style bound work). An unbounded "infinitely many X" concept is NOT engine-ready merely because instances are searchable. |
| `FORMALIZE-FIRST` | The first certifiable move is a precise Lean statement in the Brockian registry (the 25 existing targets-board statement modules are the precedent and are cited by name as evidence). `partially-formalized` concepts rank above `open` here — their first move is already done. |
| `NOT-ATTACKABLE-YET` | Honest bucket, rendered as prominently as the others: beyond current engines (Hodge, Navier–Stokes, Yang–Mills). |

- **Emits** `concepts/frontier-nominations.yaml`: generation date, measured
  counts, ranked nominations each carrying evidence (matched table row, seed
  source, live alignment count — CANDIDATE tier never counted), the
  formalization-frontier list (separate section, coverage framing), the
  excluded list, and dedupe annotations. **A proposal document only. The tool
  never writes to the database.**

### 2. Approve — Chris gate, separate artifact

Approvals live in `concepts/campaign-approvals.yaml` — hand-edited, never
regenerated (regenerating nominations can never clobber an approval). No
engine consumes budget without an entry here. Git is the audit trail.

### 3. Campaign — budgeted, engine-dispatched

For each approved nomination, a campaign brief (template in `docs/FLYWHEEL.md`)
names: the exact sub-statement, the engine (AutoLab project / Aristotle batch /
Brockian pipeline), the verifier that judges success (AXLE / lake build /
official judge), the budget cap, and the success criterion — a machine-checked
certificate, never a claim. Dispatch is manual in v0.

### 4. Certify and return — one resolver to write, then existing rails

Success is defined as **landing in the brockian-mathematics registry** under
its existing PROVED/axioms_ok/sorry_free gates. (An AXLE-attested certificate
that does not land in the registry does **not** return to the Atlas — state
this in the brief; the registry is the sole return path.)

From the registry, existing rails carry it: harvester → `atlas_statements`.
The missing link is alignment granularity: `concepts/sync_concepts.py`
matches exact `native_name`, but the 25 targets-board alignments carry Lean
**module** names while the harvester emits **declaration** names — so today a
newly proved module would land in the Atlas and never align to its concept.

**v0 builds the resolver:** extend `sync_concepts.py` so an alignment whose
`native_name` has no exact statement match is retried as a module reference —
matched against declarations whose name starts with `<native_name>.` (or whose
`module` column equals it), deterministically picking the lexicographically
first declaration, recording `resolution: module-prefix` in the alignment
evidence. Exact-match behavior is unchanged; unresolved stays ALIGNMENT
PENDING (safe, never an error).

What this stage does NOT do: mutate concept status. Status promotion
(open → partially-formalized → formalized) remains a **recorded curation act
in the seed YAML** — the Atlas's own rule that `formalized` is a judgment, not
a script output. An alignment claims formalization-of-statement; proof status
lives on the statement row (`register` fields), not on the alignment.

## v0 scope

1. `tools/nominate_frontier.py` + fixture tests (two frontiers, board_status
   join, dedupe, tiers with named sub-statements, excluded section).
2. `concepts/frontier-nominations.yaml` — first generated artifact, committed.
3. `concepts/campaign-approvals.yaml` — empty scaffold with format comment.
4. Module-prefix alignment resolution in `concepts/sync_concepts.py` + tests.
5. `docs/FLYWHEEL.md` — loop doc + campaign-brief template.
6. NOT in v0: automatic engine dispatch, DB writes from the nominator, LLM
   anything, concept-status mutation.

## Honesty constraints (inherited, restated)

- Measured numbers only, stamped with generation date; CANDIDATE alignments
  never in nomination evidence.
- `NOT-ATTACKABLE-YET` and `excluded` render as prominently as `ENGINE-READY`.
- Resolved/disputed/independent board problems are never nominated.
- The formalization frontier is always framed as coverage, never as open
  mathematics.

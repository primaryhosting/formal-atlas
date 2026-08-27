# The Formal Atlas

**A living atlas of machine-verified mathematics.** One public map where a
"place" is a mathematical concept — the Fundamental Theorem of Algebra,
the irrationality of √2 — and every machine-checked formalization of it,
in Lean/Mathlib, Metamath, the Brockian corpus, and (in time)
Isabelle/AFP, Coq/Rocq, HOL Light, and Mizar, is attached to that place
with full provenance: its native name, its kind, and a deep link into the
library's own presentation.

This repository is the harvest pipeline behind that map. It:

- **Harvests** metadata from each library's own published exports —
  metadata only; no proof bodies are redistributed (see
  `DATA-LICENSES.md`).
- **Normalizes** everything into one schema-validated statement format
  (`schema/statement.schema.json`).
- **Serves** it as public, read-only Supabase tables behind safety gates
  that refuse suspicious loads and retire — never delete — vanished
  statements.
- **Publishes** weekly numbered *editions* as GitHub Releases: frozen,
  checksummed snapshots that can be cited, diffed, and reproduced
  exactly.

Two commitments define the project:

1. **The atlas reports each library's own checked status; it never
   re-checks foreign proofs.** A row means "this library publishes this
   statement with this status," nothing more.
2. **Headline numbers are measured and tiered.** Concept↔statement
   alignments carry an evidence tier (`CURATED` / `ALIGNED` /
   `CANDIDATE`), and machine-guessed `CANDIDATE` alignments never appear
   in headline counts.

**Start here:**

- Architecture, schema, safety gates, and the how-to-add-a-harvester
  recipe: [`docs/PIPELINE.md`](docs/PIPELINE.md)
- Epistemic method (inclusion criteria, tiers):
  [METHOD page](https://github.com/primaryhosting/brockian-mathematics/blob/main/docs/atlas/METHOD.md)
- The map itself: <https://torus.riemannlab.com/atlas>
- Data licensing: [`DATA-LICENSES.md`](DATA-LICENSES.md)

```bash
# dev setup
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q          # no network; fixtures are verbatim upstream excerpts

# run a harvester against its fixture
.venv/bin/python harvesters/metamath/harvest.py \
  --source tests/fixtures/set_mm_excerpt.mm --out /tmp/out/metamath
```

## Harvested libraries

| Library | Granularity | Rows | Source | Subject codes |
|---------|-------------|------|--------|---------------|
| brockian | statement | verified-registry PROVED entries | `torus.riemannlab.com/verified-registry.json` | MSC 2020 via `atlas.msc` module-path mapper |
| metamath | statement | set.mm `$a`/`$p` statements | metamath/set.mm | MSC 2020 via `atlas.msc` section-banner mapper |
| mathlib | statement | declaration index | leanprover-community/mathlib4 | MSC 2020 via `atlas.msc` module-prefix mapper |
| afp | **entry** (whole development) | 1,025 entries (2026-08-26) | `isa-afp.org/entries/index.json` | AFP topic tags |
| coq | **package** | 586 opam packages | `rocq-prover.org/opam/released/index.tar.gz` | none at package granularity |

**Coverage honesty:** `afp` rows are whole entries and `coq` rows are opam
packages (both `kind=other`), NOT individual theorems — they must never be
summed into statement-level headline counts. Subject codes are populated only
where the mapping tables reach (metamath rows inherit their enclosing banner
title; mathlib infrastructure modules are deliberately uncoded; brockian
coverage is currently sparse) — "N statements with subject codes" must be
measured from output, never assumed to be 100%.

## Concept seeds

- `concepts/wiedijk100.yaml` — Wiedijk's 100 Theorems, with informal statements.
- `concepts/targets-board.yaml` — 104 problems from the Riemann Lab `/targets`
  board. Regenerate:
  `python tools/build_targets_seed.py --source tests/fixtures/targets_board.json --out concepts/targets-board.yaml`

`concepts/sync_concepts.py` globs `concepts/*.yaml`, so new seed files sync
automatically wherever the concept sync runs.

## Candidate alignments

`concepts/candidates-metamath.yaml` holds machine/curation-proposed
concept↔statement alignments at **CANDIDATE tier only** — they never count in
headline numbers until a human promotes them. Regenerate (network + live table
required, must run after a metamath harvest+load):
`python tools/propose_candidates.py` (flags: `--concepts`, `--out`,
`--max-proposals`).

## Editions

The atlas ships weekly versioned dataset releases ("editions"). Each edition is a
GitHub Release containing the normalized `statements.jsonl` files and their
manifests (source version, statement count, harvest timestamp, sha256 checksum)
for every harvested library, so any snapshot of the atlas can be cited, diffed,
and reproduced exactly.

## Links

- Pipeline internals: [`docs/PIPELINE.md`](docs/PIPELINE.md)
- Method page: https://github.com/primaryhosting/brockian-mathematics/blob/main/docs/atlas/METHOD.md
- Site: https://torus.riemannlab.com/atlas
- Epistemic framework paper: https://github.com/primaryhosting/euler-sair-stage2/blob/main/CONTRIBUTION-PACK/1-PAPER/mathematics-in-the-age-of-mechanical-reproduction.pdf

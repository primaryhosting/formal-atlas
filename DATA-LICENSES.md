# Data Licenses

The atlas performs **metadata-only harvesting**: names, kinds, statement strings,
and links back to each library's own source. No proof bodies are redistributed.

| Library | Upstream | License |
|---------|----------|---------|
| Brockian registry | `torus.riemannlab.com/verified-registry.json` (sanitized public export — the raw internal registry is never read for public display) | Project-owned |
| Metamath set.mm | metamath/set.mm | CC0 (public domain) |
| Mathlib | leanprover-community/mathlib4 | Apache-2.0 |
| Isabelle AFP | `isa-afp.org/entries/index.json` (entry METADATA only: titles, authors, topics — no proof text) | Per-entry: BSD-3-Clause OR LGPL at the author's choice (https://www.isa-afp.org/about/). The per-entry license string is NOT in the harvested index; capturing it (metadata/entries/<name>.toml in the AFP devel repo) is deferred — until then the atlas carries entry name + link only. |
| Coq/Rocq opam | rocq-prover/opam `released` repo (`index.tar.gz`) — package names + synopses only (facts/metadata) | Repo metadata under the repo's terms; individual packages carry their own licenses (per-package `license:` fields in opam files, many "Unknown") |

## First-party data and test fixtures

- `concepts/targets-board.yaml` — first-party board data (Chris Brock's riemannlab
  Lovable project `dd8308ac`, `src/data/top100-problems.json`, snapshot
  `as_of 2026-08-06`). No third-party license applies.
- `concepts/candidates-metamath.yaml` — original curation, informed by Metamath's
  public "100 Theorems" page (mm_100.html), cited in the file header.
- `tests/fixtures/set_mm_head.mm` — ~150 KB verbatim excerpt of set.mm
  (metamath/set.mm, develop branch, fetched 2026-08-27). set.mm is CC0 1.0 Universal.

## Rule for later libraries (AFP and similar)

For libraries with per-entry licensing (e.g. the Isabelle Archive of Formal
Proofs), the harvester collects names, entry, authors, and the per-entry license
string. Statement bodies are included in releases only where the entry's license
permits; otherwise the atlas carries the name + link only.

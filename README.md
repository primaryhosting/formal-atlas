# The Formal Atlas — pipeline

The Formal Atlas is a living atlas of all formally verified mathematics: one public
map where a "place" is a mathematical statement (a concept), and every
machine-checked verification of it — in Lean/Mathlib, Isabelle/AFP, Coq/Rocq,
Metamath, HOL Light, Mizar, or the Brockian corpus — is attached to that place with
full provenance. This repository is the harvest pipeline: it pulls metadata from
each library, normalizes it into a common schema, and publishes it as queryable
tables and versioned dataset editions.

**The atlas reports each library's own checked status; it never re-checks foreign proofs.**

## Architecture

```
 +--------------------------------------------------+
 |             GitHub Actions harvesters            |
 |  brockian | metamath (set.mm) | mathlib | ...    |
 +------------------------+-------------------------+
                          |
            statements.jsonl + manifest.json
                          |
                          v
 +--------------------------------------------------+
 |        Supabase atlas_* tables (anon read)       |
 +------------------------+-------------------------+
                          |
                          v
 +--------------------------------------------------+
 |        torus.riemannlab.com /atlas  (site)       |
 +--------------------------------------------------+

  plus: JSON editions published as GitHub Releases
```

## Editions

The atlas ships weekly versioned dataset releases ("editions"). Each edition is a
GitHub Release containing the normalized `statements.jsonl` files and their
manifests (source version, statement count, harvest timestamp, sha256 checksum)
for every harvested library, so any snapshot of the atlas can be cited, diffed,
and reproduced exactly.

## Links

- Method page: https://github.com/primaryhosting/brockian-mathematics/blob/main/docs/atlas/METHOD.md
- Site: https://torus.riemannlab.com/atlas
- Epistemic framework paper: https://github.com/primaryhosting/euler-sair-stage2/blob/main/CONTRIBUTION-PACK/1-PAPER/mathematics-in-the-age-of-mechanical-reproduction.pdf

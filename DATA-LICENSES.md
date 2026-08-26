# Data Licenses

The atlas performs **metadata-only harvesting**: names, kinds, statement strings,
and links back to each library's own source. No proof bodies are redistributed.

| Library | Upstream | License |
|---------|----------|---------|
| Brockian registry | primaryhosting/brockian-mathematics `registry/theorems.json` | Project-owned |
| Metamath set.mm | metamath/set.mm | CC0 (public domain) |
| Mathlib | leanprover-community/mathlib4 | Apache-2.0 |

## Rule for later libraries (AFP and similar)

For libraries with per-entry licensing (e.g. the Isabelle Archive of Formal
Proofs), the harvester collects names, entry, authors, and the per-entry license
string. Statement bodies are included in releases only where the entry's license
permits; otherwise the atlas carries the name + link only.

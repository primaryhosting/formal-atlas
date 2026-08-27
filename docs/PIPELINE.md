# The Formal Atlas pipeline

This document is the architecture reference for the `formal-atlas` repository.
It is written for a first-time contributor who is a capable engineer but new to
formal-mathematics tooling. Reading it top to bottom should leave you able to
answer three questions: *what does this pipeline claim, how does it avoid
claiming more than it knows, and how do I extend it without breaking either?*

The one-sentence summary: **the atlas harvests metadata from formal-proof
libraries, normalizes it into one schema, loads it into public tables behind a
set of safety gates, and publishes citable weekly snapshots — and it reports
each library's own checked status; it never re-checks foreign proofs.**

---

## 1. The flow: harvest → align → serve

Three stages, three kinds of artifact:

- **Harvest** — per-library scripts read one upstream export each and emit a
  normalized, schema-validated `statements.jsonl` + `manifest.json` pair.
- **Align** — human-curated concept seeds (`concepts/*.yaml`) attach harvested
  statements to *concepts* ("the Fundamental Theorem of Algebra" as a place on
  the map), each attachment carrying an explicit evidence tier.
- **Serve** — a loader upserts everything into Supabase `atlas_*` tables
  (world-readable, anon `SELECT`-only), the site renders them, and a weekly
  workflow freezes the harvested files into a numbered GitHub Release
  ("edition") so any snapshot can be cited and reproduced.

```
        upstream libraries (each library's own published exports)
   ┌────────────────┬──────────────────────┬───────────────────────────┐
   │ brockian       │ metamath             │ mathlib                   │
   │ verified-      │ set.mm (raw text,    │ doc-gen4                  │
   │ registry.json  │ streamed)            │ declaration-data          │
   └───────┬────────┴──────────┬───────────┴─────────────┬─────────────┘
           │                   │                         │
           v                   v                         v
   harvesters/<lib>/harvest.py          (one script per library)
           │
           │  every harvester funnels through ONE writer:
           v
   atlas/emit.py  write_harvest()  ── JSON-Schema validation at emit time
           │
           │  out/<lib>/statements.jsonl  +  out/<lib>/manifest.json
           v
   atlas/load.py  ────────────── safety gates ──────────────┐
           │        empty-harvest refusal · ±20% delta gate │
           │        retire-not-delete · scoped writes       │
           v                                                │
   ┌──────────────────────────────────────────────┐         │
   │ Supabase  atlas_* tables (anon read-only)    │ <───────┘
   │  atlas_libraries    atlas_statements         │
   │  atlas_concepts     atlas_alignments         │  <── concepts/sync_concepts.py
   │  atlas_harvest_runs                          │      (seed YAMLs → concepts
   └──────────────────────┬───────────────────────┘       + tiered alignments)
                          │
            ┌─────────────┴──────────────┐
            v                            v
   torus.riemannlab.com/atlas    GitHub Releases: edition-N
   (the living site)             (weekly citable snapshots,
                                  stamped back into the DB by
                                  atlas/edition.py)
```

Two further libraries follow the same funnel (the diagram shows the original
three): **afp** (`isa-afp.org/entries/index.json`, entry-level — one row per
whole AFP development) and **coq** (`rocq-prover.org/opam/released/index.tar.gz`,
package-level — one row per opam package). Both emit `kind=other` rows that
must never be counted alongside statement-level theorem counts.

Everything above the Supabase box runs in GitHub Actions
(`.github/workflows/harvest.yml` on a schedule, `edition.yml` weekly) or on a
developer machine with the same commands. Nothing below the Supabase box has
write access: the serving surface is read-only by construction (RLS `SELECT`
policies for `anon`, no write grants).

### Where the code lives

| Piece | Path | Role |
|---|---|---|
| Harvesters | `harvesters/{brockian,metamath,mathlib}/harvest.py` | one upstream → normalized rows |
| Emit gate | `atlas/emit.py` | the *only* writer of `statements.jsonl` + `manifest.json`; validates every row |
| Loader | `atlas/load.py` | plan (pure) + apply (network); both transports |
| Edition stamp | `atlas/edition.py` | `python -m atlas.edition --tag N` after a release |
| Concept seeds | `concepts/*.yaml`, `concepts/sync_concepts.py` | curated concepts + alignments |
| Seed builder | `tools/build_wiedijk_seed.py` | regenerates the Wiedijk-100 seed from mathlib's `docs/100.yaml` |
| Schemas | `schema/statement.schema.json`, `schema/manifest.schema.json` | the contract, machine-checked |
| DB shape | `migrations/001_atlas_tables.sql` | tables, RLS, seed library rows |
| Tests | `tests/` (fixtures in `tests/fixtures/`) | no network; fixtures are verbatim upstream excerpts |

---

## 2. The normalized schema

Every library, whatever its native format, is reduced to one row shape. The
authoritative contract is `schema/statement.schema.json` (JSON Schema
2020-12), enforced by `atlas.emit.write_harvest()` on every single row —
a harvester emitting garbage fails loudly at emit time, before anything
touches the database.

### Statement fields

| Field | Required | Semantics |
|---|---|---|
| `library` | yes | Library id, from a closed enum (`brockian`, `metamath`, `mathlib`, `afp`, `coq`, `hollight`, `mizar`). Adding a library means widening this enum deliberately, in review — not ad hoc. |
| `native_name` | yes | The statement's name *in its own library* (`irrational_sqrt_two`, `ax-1`). `(library, native_name)` is the natural key: unique per harvest (emit raises on duplicates) and unique in the DB (`unique (library_id, native_name)`). The atlas never invents names. |
| `kind` | yes | One of `theorem`, `definition`, `axiom`, `lemma`, `corollary`, `other`. Each harvester maps its library's native taxonomy into this set and maps anything unrecognized to `other` rather than guessing — `other` is an honest answer. |
| `statement_text` | no (nullable) | The statement as the library states it, when the upstream export carries it. Metamath rows have the math string; mathlib's declaration export carries no statement text, so mathlib rows have `null` — stated, not papered over. |
| `module` | no (nullable) | Positional context inside the library: a Mathlib module path, a set.mm chapter header. Whatever the library itself uses. |
| `source_url` | yes | Deep link to the statement *in the library's own presentation* (schema-enforced `https://`). Provenance is a load-bearing feature: every atlas row can be checked against its source in one click. |
| `subject_codes` | no (default `[]`) | Subject classification codes. How they were (or were not) derived is declared per-harvest in the manifest's `subject_derivation` — e.g. the brockian harvester declares "MSC 2020 codes from registry module path via atlas.msc.brockian_msc prefix/segment table; unmapped modules carry no codes". |

Rows are emitted sorted by `native_name` with sorted JSON keys, so
`statements.jsonl` is deterministic for a given input: identical harvests are
byte-identical, and the manifest's checksum is meaningful.

### Manifest fields

`write_harvest()` also emits `manifest.json` (contract:
`schema/manifest.schema.json`):

| Field | Semantics |
|---|---|
| `library` | matches every row (emit raises on mismatch) |
| `harvester_version` | version of the harvesting *code* |
| `source_version` | identifies what upstream state was harvested: an ETag or `Last-Modified` for URL sources, the file name for local fixtures, a schema tag for the brockian registry. This is what makes a harvest citable. |
| `statement_count` | measured count of emitted rows — never estimated |
| `harvested_at` | UTC timestamp |
| `sha256` | checksum of `statements.jsonl`, so an edition tarball can be verified byte-for-byte |
| `subject_derivation` | one honest sentence about how `subject_codes` were derived for this library |

### Serving tables

`migrations/001_atlas_tables.sql` defines five tables:

- **`atlas_libraries`** — one row per library: name, prover, url, license,
  plus bookkeeping the loader maintains (`statement_count`,
  `last_harvest_at`, `harvester_version`).
- **`atlas_statements`** — the normalized rows, plus lifecycle columns the
  pipeline owns: `retired`, `first_seen_edition`, `last_seen_edition`.
- **`atlas_concepts`** — the map's places: slug, title, informal statement,
  optional Wiedijk number / Wikidata id / MSC code, `seed_source`, `status`.
- **`atlas_alignments`** — concept ↔ statement edges with a `tier`
  (`CURATED` / `ALIGNED` / `CANDIDATE`, DB-enforced check constraint) and an
  `evidence` JSONB blob recording *why* the edge exists.
- **`atlas_harvest_runs`** — an append-only run log: source version, counts
  seen/added/retired, status (`ok` / `failed`), later stamped with
  `edition_tag`. Failures are recorded too — the run history is honest about
  runs that produced nothing.

All five have RLS enabled with anon `SELECT`-only policies: the public can
read everything and write nothing.

---

## 3. The safety gates

The loader treats the database as a public record that must never silently
lose or misstate history. Four mechanisms enforce that. The planning half
(`atlas.load.plan_upsert()`) is a pure function — no I/O — so every gate is
unit-tested without a network.

### 3.1 Empty-harvest refusal

`plan_upsert()` raises if the harvest is empty but the library has live rows.

**Why:** the most likely cause of an empty harvest is not "the library deleted
all its mathematics" — it is an upstream URL moving, a format change, or a
transient failure. Without this gate, one bad fetch would retire an entire
library's history in a single scheduled run. The pipeline prefers to fail
loudly and load nothing.

### 3.2 The ±20% delta gate

If the harvested count differs from the live count by more than ±20%, the
load refuses unless explicitly overridden (`--allow-big-delta`, or
`ATLAS_ALLOW_BIG_DELTA=1`, surfaced as a `workflow_dispatch` input).

**Why:** libraries grow by small increments run to run. A sudden ±20% swing
almost always means the harvester is misparsing a changed upstream format —
seeing half the file, or double-counting. The gate converts "silently publish
wrong numbers" into "a human looks first, then reruns with the override."
The override is deliberately explicit and per-run: it is a reviewed decision,
never a default.

The baseline for the delta is **live rows only** (`retired = false`). Using
an all-time baseline would inflate the denominator with retired rows until
the gate tripped on every run — and would re-retire the historical backlog
each run.

### 3.3 Retire, never delete

Statements that vanish from a harvest are marked `retired = true` — scoped
to the harvested library, and only for names in the computed retire set.
Rows are never deleted. Reappearing statements un-retire: every upserted row
sets `retired = false`, and the upsert's `merge-duplicates` semantics keep
columns the payload omits (like the edition stamps).

**Why:** the atlas is a record, and records that delete their past cannot be
audited. A statement renamed upstream, temporarily dropped, or removed on
purpose stays queryable with its full history (`first_seen_edition`,
`last_seen_edition`, `retired`). Retirement is also what makes the delta gate
recoverable — a wrongly retired batch is one un-retiring harvest away from
restoration, not a restore-from-backup incident. Library scoping on the
retire write is mandatory in both transports: an unscoped name filter could
retire same-named statements in *other* libraries.

### 3.4 Edition stamping

Weekly, `edition.yml` harvests everything fresh, packages it as
`edition-N` (a GitHub Release containing the `statements.jsonl` files and
manifests), and then `python -m atlas.edition --tag N` stamps the database:

1. `last_seen_edition = N` on every live row — unconditionally. (No
   "changed-only" filter: PostgREST's `neq` excludes NULLs, and rows begin
   with a NULL stamp, so a guarded update would no-op forever. The
   unconditional write is the correct one, and the docstring in
   `atlas/edition.py` says why.)
2. `first_seen_edition = N` where still NULL — the first edition a row
   appeared in.
3. `edition_tag = N` on `ok` harvest runs not yet stamped.

**Why:** editions turn a continuously mutating dataset into citable science.
"Edition 12 of the atlas" is a fixed artifact with per-library counts,
source versions, and checksums; a paper can cite it, a reader can download
the exact tarball, and the DB stamps let anyone reconstruct which statements
were live in which edition. One accepted v0 caveat, documented in
`edition.yml`: the release tarball is a fresh harvest while the DB stamp
covers the latest scheduled loads, so the two can differ by a few hours of
upstream drift.

### 3.5 Honest failure recording

Recording a failed run is the *caller's* job (the workflow's `if: failure()`
step runs `atlas.load --record-failure`), while `load()` records only
successful runs — so a failure never produces duplicate failure rows, and a
concept-sync failure after a successful load fails the CI job without
fabricating a failed *harvest* row. The run log states exactly what happened,
no more.

---

## 4. Transports: PostgREST and the ingest function

All writes go through one of two transports, resolved from the environment by
`atlas.load.require_transport()`:

- **Direct PostgREST mode** — `ATLAS_SUPABASE_URL` +
  `ATLAS_SUPABASE_SERVICE_KEY`. Privileged writes straight to
  `/rest/v1/...` with the service-role key. House pattern: every request
  sends the key in **both** `apikey` and `Authorization: Bearer` headers,
  and every read paginates unconditionally (`get_paged`) because PostgREST
  caps single responses server-side and a one-shot read silently truncates.
- **Ingest mode** — `ATLAS_INGEST_URL` + `ATLAS_INGEST_TOKEN`. All
  privileged writes are POSTed as `{action, ...}` payloads to a deployed
  `atlas-ingest` edge function, authenticated with an `x-atlas-token`
  header. Ingest mode wins when both pairs are set.

The two transports execute the **same plan and the same row mapping** —
`load()` computes one plan and one payload, and only the wire calls differ.
The edge function implements the same verbs (`existing`, `upsert`, `retire`,
`library_meta`, `run_insert`, `edition`) with server-side pagination and
per-call batch caps.

**Why ingest mode exists — and why the service key never leaves the managed
environment:** the serving database is Lovable-Cloud-managed, and no
service-role key exists in CI in that configuration. That is a feature, not a
workaround. The service-role key bypasses RLS entirely; a copy in GitHub
Actions secrets would make every workflow, every action in the supply chain,
and every log line a potential path to unrestricted database writes. The
ingest function inverts the exposure: CI holds only a narrow bearer token
whose entire capability is "the six atlas verbs, with the edge function's
own validation and batch caps in the way." The key that can do anything stays
inside the managed environment that already holds it; the credential that
travels can only do atlas ingestion. Revoking or rotating the token costs
nothing; leaking it bounds the blast radius to tables that are already
rebuild-from-harvest reproducible.

One consequence to know: `concepts/sync_concepts.py` is PostgREST-only (the
ingest function has no concept/alignment verbs yet), so in ingest-only CI it
deliberately prints a skip message and exits cleanly rather than failing the
job.

The single HTTP layer (`headers` / `get_paged` / `post` / `patch` /
`ingest_call`) lives in `atlas/load.py`; `sync_concepts.py` and
`edition.py` import it rather than duplicating header or pagination code.
Keep it that way.

---

## 5. Epistemics: tiers and the headline rule

The atlas's product is honesty, so its claims are typed.

**What a statement row claims.** Exactly this: *the named library, at the
recorded `source_version`, published this name with this kind, and here is
the link.* The atlas reports each library's own checked status — it never
re-checks foreign proofs, and it never claims a proof is correct beyond what
the library itself asserts. The brockian harvester is the strictest case: it
reads only the prover-owned sanitized public registry and admits only entries
that are `PROVED`, `axioms_ok`, and `sorry_free` — everything else "is not
machine-verified mathematics and is not the atlas's to report."

**What an alignment claims.** Alignments carry a tier, checked at the
database level:

| Tier | Meaning |
|---|---|
| `CURATED` | A human, or a library's own curated mapping (e.g. mathlib's `docs/100.yaml`), asserts this statement formalizes this concept. Evidence recorded in the `evidence` blob. |
| `ALIGNED` | An evidence-backed alignment below the curated standard; the exact criteria are defined on the METHOD page, not here. |
| `CANDIDATE` | A machine guess awaiting review. |

**The headline rule: `CANDIDATE` never appears in headline counts.** Any
surfaced number — "N concepts formalized", per-library totals, site
statistics — counts only `CURATED` and `ALIGNED` edges. Candidates are
visible as candidates, never aggregated into claims. The same restraint runs
through the seeds: the Wiedijk-100 builder never emits status `formalized` —
a mathlib alignment yields at most `partially-formalized`, because promotion
to "formalized" is a curation judgment, not a script's; and
`informal_statement` is never auto-filled.

Coverage is stated, not implied. A partial harvest says exactly what it
covers: mathlib rows carry `statement_text: null` because the upstream
export has none; the manifest's `subject_derivation` states exactly how far
the subject-code mapping tables reach (unmapped modules carry no codes, and
coq declares no subject taxonomy at package granularity at all);
unresolvable alignments are reported as
`PENDING`, never silently dropped or errored.

The full epistemic framework — inclusion criteria, tier definitions, and
the verification standard behind the brockian registry — lives on the METHOD
page:
<https://github.com/primaryhosting/brockian-mathematics/blob/main/docs/atlas/METHOD.md>.
When this document and METHOD disagree, METHOD wins.

---

## 6. How to add a harvester

The recipe, in the order the work actually goes well.

### 6.1 Probe before you write (probe-then-adapt)

Do not design from documentation or memory — upstream exports lie about
themselves (mathlib's declaration export is JSON served with a `.bmp`
extension and an `image/bmp` content type). Probe the real artifact first,
cheaply:

```bash
# headers only: size, content type, ETag
curl -sI https://upstream.example/export.json
# ranged bytes: inspect the real shape without downloading the file
curl -s -r 0-400000 https://upstream.example/export.json | head -c 2000
```

Disk and bandwidth are limited: **never download a large upstream file to a
dev machine** (the mathlib export is ~67 MB; set.mm is streamed line-by-line
in CI for the same reason). Ranged-byte probes are enough to learn the
format. Then **record the probe evidence in the harvester's module
docstring** — date, URL, observed size, observed shape, observed kind
distribution. See `harvesters/mathlib/harvest.py` for the model. Future
maintainers debugging a format drift start from your measurements, not your
assumptions.

### 6.2 The contract

A harvester is one file, `harvesters/<lib>/harvest.py`, that:

1. Reads **one upstream source** — a URL by default, a local path for tests
   (the same `--source` flag serves both; fixtures exercise the full path).
2. Maps each entry to a statement dict per §2. Map unknown kinds to
   `other`; set fields you don't have to `None`; never fabricate.
3. Derives `source_version` from real provenance: `ETag` or
   `Last-Modified` for URLs, the file name for local sources, an upstream
   schema/commit id when the source declares one. `"unknown"` is the honest
   last resort, not the default choice.
4. Calls the single writer — nothing else ever writes harvest files:

   ```python
   from atlas.emit import write_harvest

   write_harvest(out_dir, "<lib>", rows,
                 harvester_version=HARVESTER_VERSION,
                 source_version=src_ver,
                 subject_derivation="one honest sentence, or None")
   ```

5. Exposes a `harvest(source=DEFAULT_SOURCE, out_dir="out/<lib>")` function
   plus an `argparse` CLI with `--source` / `--out` (this exact signature is
   what the workflow matrix and the tests both call).
6. Validates upstream preconditions loudly: if the source declares a schema
   tag, check it and abort on mismatch (see the brockian harvester) rather
   than best-effort parsing a format you no longer understand.

`write_harvest()` gives you row-level JSON-Schema validation, duplicate-name
rejection, library-consistency checks, deterministic ordering, and the
manifest — for free. Do not reimplement any of it.

### 6.3 Fixture rules and tests (TDD)

Write the failing test first, then the parser.

- Fixtures in `tests/fixtures/` must **copy the real upstream format
  verbatim** — a trimmed excerpt of the actual artifact, preserving its
  genuine conventions, never a simplified invention. The set.mm fixture
  keeps real chapter banners, `$c`/`$v` declarations, and scoping blocks;
  that is why the parser's section-header handling is actually tested.
  Keep fixtures small (the suite ships kilobyte-scale excerpts of
  megabyte-scale sources).
- **No network in unit tests.** Tests call `harvest(source=<fixture path>)`;
  the URL branch is exercised only in CI's real runs. Loader tests
  monkeypatch the transport and assert on the call sequence.
- Test at minimum: field mapping (names, kinds, modules, URLs), the edge
  cases your probe revealed, malformed-input failure modes (parsers must
  raise on truncated input, not emit partial data), and one end-to-end
  `harvest()` → valid `statements.jsonl` + manifest run against the fixture.
- Run the full suite before handing off: `.venv/bin/pytest -q` — it must be
  fully green; never trade an existing pass for a new feature.

### 6.4 Wiring (owned by shared files)

Landing a harvester also requires edits to shared, integrator-owned files:

- `schema/statement.schema.json` — add the library id to the `library` enum
  (if not already present).
- `migrations/…` / the live DB — an `atlas_libraries` row (id, name,
  prover, url, license).
- `.github/workflows/harvest.yml` — the library in the `plan` job's
  allowlist `case` and default matrix list.
- `.github/workflows/edition.yml` — the harvest line in "Harvest all
  libraries".
- `DATA-LICENSES.md` — the upstream license row; for per-entry-licensed
  libraries (AFP and similar), follow the rule already written there:
  statement bodies only where the entry's license permits, otherwise
  name + link only.
- `README.md` — the library list, if it names libraries.

### 6.5 Honest deferral

Not everything must ship in the first cut — but every deferral must be
**stated, in writing, at the point of use**, never silently faked:

- No statement text in the upstream export → emit `statement_text: None`
  and say so in the module docstring (mathlib pattern).
- Subject codes not yet derivable → empty `subject_codes` and a
  `subject_derivation` that says exactly that (coq pattern: `null`, with
  the harvester noting there is no subject taxonomy at package granularity).
- Can only harvest a subset (one archive section, one export flavor) →
  harvest the subset and state precisely what it covers. A partial harvest
  that declares its coverage is correct; a partial harvest presented as
  complete is a bug of the worst kind here.
- Cannot meet the contract honestly at all → **defer the library** and
  write down why. "Not yet harvested, because X" is a valid, respectable
  state for a library to be in. Wrong data is not.

---

## 7. Proposed README

*This section is a draft replacement for the top of `README.md`. The
integrator decides whether to apply it; this repo's beauty track does not
edit `README.md` directly.*

> # The Formal Atlas
>
> **A living atlas of machine-verified mathematics.** One public map where a
> "place" is a mathematical concept — the Fundamental Theorem of Algebra,
> the irrationality of √2 — and every machine-checked formalization of it,
> in Lean/Mathlib, Metamath, the Brockian corpus, and (in time)
> Isabelle/AFP, Coq/Rocq, HOL Light, and Mizar, is attached to that place
> with full provenance: its native name, its kind, and a deep link into the
> library's own presentation.
>
> This repository is the harvest pipeline behind that map. It:
>
> - **Harvests** metadata from each library's own published exports —
>   metadata only; no proof bodies are redistributed (see
>   `DATA-LICENSES.md`).
> - **Normalizes** everything into one schema-validated statement format
>   (`schema/statement.schema.json`).
> - **Serves** it as public, read-only Supabase tables behind safety gates
>   that refuse suspicious loads and retire — never delete — vanished
>   statements.
> - **Publishes** weekly numbered *editions* as GitHub Releases: frozen,
>   checksummed snapshots that can be cited, diffed, and reproduced
>   exactly.
>
> Two commitments define the project:
>
> 1. **The atlas reports each library's own checked status; it never
>    re-checks foreign proofs.** A row means "this library publishes this
>    statement with this status," nothing more.
> 2. **Headline numbers are measured and tiered.** Concept↔statement
>    alignments carry an evidence tier (`CURATED` / `ALIGNED` /
>    `CANDIDATE`), and machine-guessed `CANDIDATE` alignments never appear
>    in headline counts.
>
> **Start here:**
>
> - Architecture, schema, safety gates, and the how-to-add-a-harvester
>   recipe: [`docs/PIPELINE.md`](docs/PIPELINE.md)
> - Epistemic method (inclusion criteria, tiers):
>   [METHOD page](https://github.com/primaryhosting/brockian-mathematics/blob/main/docs/atlas/METHOD.md)
> - The map itself: <https://torus.riemannlab.com/atlas>
> - Data licensing: [`DATA-LICENSES.md`](DATA-LICENSES.md)
>
> ```bash
> # dev setup
> python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
> .venv/bin/pytest -q          # no network; fixtures are verbatim upstream excerpts
>
> # run a harvester against its fixture
> .venv/bin/python harvesters/metamath/harvest.py \
>   --source tests/fixtures/set_mm_excerpt.mm --out /tmp/out/metamath
> ```

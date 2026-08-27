# Frontier proposals — the next five moves

> Scout output from the pipeline swarm, 2026-08-27. Companions:
> [`docs/PIPELINE.md`](PIPELINE.md) (architecture),
> [METHOD](https://github.com/primaryhosting/brockian-mathematics/blob/main/docs/atlas/METHOD.md)
> (epistemics — when this document and METHOD disagree, METHOD wins).
>
> These are proposals, not commitments. Each names its cost and its failure
> mode up front, in keeping with the house rule: stated gaps, not decorated
> ones.

The atlas exists inside a larger loop: **prove** (Aristotle / the Brockian
prover / AutoLab-driven solvers) → **verify** (AXLE kernel attestation) →
**remember** (the atlas: statements, alignments, editions) → **aim** (the
frontier view selects what to prove next). Today the loop is open at both
ends — the atlas remembers but does not yet feed targets back to the provers,
and its memory of the non-Lean world is shallow (AFP at entry level, Coq at
package level). Every proposal below closes or thickens one segment of that
loop.

---

## 1. Statement-level AFP deepening — make Isabelle a real peer

**What.** Replace the entry-level AFP harvest (one row per whole AFP
development, `kind=other`) with a statement-level harvest: one row per named
Isabelle theorem, with `kind`, theory-file `module`, and a deep link into the
AFP's own HTML presentation. Target order: AFP first (it has the richest
theorem-per-entry density outside Mathlib), Coq/Rocq statement level as the
follow-on using the same playbook.

**Why it compounds.** Everything downstream is starved without this.
Cross-library gap mining (proposal 2) is meaningless when one of the two
largest libraries is opaque below the entry level; LLM alignment (proposal 3)
has nothing to match against; and the frontier view (proposal 4) cannot say
"formalized in Isabelle but nowhere else" — currently one of the most common
true statements in formal mathematics. This is the single move that turns the
atlas from "Mathlib + Metamath + Brockian, with placeholders" into a map of
the actual formal world. It also exercises the deferral machinery honestly:
today's `kind=other` AFP rows retire naturally under the retire-not-delete
gate as statement rows land.

**Mechanism.**
- Probe-then-adapt (PIPELINE §6.1) against the AFP's published artifacts.
  Two candidate sources, in preference order: (a) the AFP's generated
  per-entry HTML/`theories` listings, which name every theorem and are
  stable-linkable; (b) an Isabelle `dump` / export run in CI (heavier —
  hours of Actions time — but yields pretty-printed statement text).
  Start with (a): names + kinds + links, `statement_text: None`, stated in
  the manifest — the mathlib pattern exactly.
- New `harvesters/afp/harvest_statements.py` funneling through
  `atlas.emit.write_harvest()` like every other harvester; verbatim fixture
  excerpt of a real AFP entry page; the existing ±20% delta gate will trip on
  the entry→statement transition, so the first load is an explicit
  `--allow-big-delta` reviewed run — which is what the override exists for.
- License discipline per `DATA-LICENSES.md`: AFP is per-entry licensed;
  harvest names/links for all entries, statement bodies only where the
  entry's license permits.

**Honest cost.** The largest single engineering item on this list: ~1–2 weeks
of focused work (probe, parser, fixtures, tests, wiring, first gated load),
plus ongoing CI minutes (the AFP index is large but public-repo Actions are
free). If route (b) is ever taken, add hours of CI per harvest and real
maintenance exposure to Isabelle version churn.

**What could go wrong.** The AFP's HTML is generated but not a contract — a
site regeneration could silently change structure (the loud-validation rule
and golden fixtures are the defense, but expect drift). Theorem *naming* in
Isabelle is less stable than Lean's (locale-qualified names, unnamed lemmas),
so the `(library, native_name)` identity key will see more retire+add churn
than Mathlib; report retired counts per edition, don't headline them.
Biggest risk: statement counts across libraries invite naive comparison
("Isabelle has N, Lean has M") that the granularity differences don't
support — every per-library count must keep its granularity note.

---

## 2. Cross-library proof-gap mining — theorems proved in exactly one system

**What.** A derived, versioned dataset (and `/atlas` view): concepts with at
least one CURATED/ALIGNED verification in **exactly one** library. These are
the atlas's most actionable products — each is simultaneously (a) a known-true,
known-formalizable statement, (b) a concrete translation target for every
other system, and (c) a benchmark item where ground truth exists in another
prover's terms. Publish it as `gaps.jsonl` in every edition: concept, the one
attesting library, native name, source link, and the list of absent systems.

**Why it compounds.** This is the "aim" segment made mechanical. Single-system
theorems are the cheapest high-value prover targets in existence: the
statement is already vetted (someone formalized it once), difficulty is
bounded (a full formal proof exists somewhere), and success produces a new
ALIGNED edge — which flows straight back into the atlas as a headline-eligible
alignment *with the strongest possible evidence* (two independent kernels).
For the Brockian corpus specifically, the gap list is a ranked menu of "where
can Brockian extend the world corpus next with high confidence of success" —
exactly the highlighted-layer story. And the gap dataset is itself the seed
for proposals 3 and 4.

**Mechanism.**
- Pure derivation, no new harvesting: a `tools/build_gaps.py` that reads
  `atlas_concepts` + `atlas_alignments` (CURATED + ALIGNED only — CANDIDATE
  never defines a gap, per the headline rule) and emits the gap set. Wiedijk
  already hand-tracks this for his 100; the atlas generalizes it to every
  concept it curates.
- Rank gaps by a transparent, stated score: number of absent systems ×
  concept seed source (Wiedijk-numbered concepts first) — no opaque ML
  ranking in v1; the METHOD-page instinct is that selection should be
  inspectable.
- Attach `gaps.jsonl` + its derivation manifest to each weekly edition
  release; add `/atlas/frontier` a "single-system" tab reading the same
  Supabase data.

**Honest cost.** Small: 2–3 days for the derivation tool, tests, edition
wiring, and the frontend tab. The real cost is prerequisite: the gap list is
only as good as concept coverage, and at v0's ~200 curated concepts it will
be short. That's fine — ship it small and honest; it grows with every
alignment.

**What could go wrong.** The subtle failure is **false gaps**: a theorem
proved in three libraries but aligned in one *looks* single-system. A gap
row is therefore a claim about the atlas's alignment coverage, not about the
world — the page must say so verbatim ("no alignment recorded in the other
systems," never "not formalized elsewhere"). Second failure: statement-strength
mismatches — the one existing verification may be a weaker form, making the
"known formalizable" premise wrong for the full concept; the tier-down rule
and alignment evidence notes are the existing defense, and gap rows should
surface the evidence note inline.

---

## 3. LLM alignment at scale — with measured verification economics

**What.** The v1 CANDIDATE proposer from the design spec, built as a
first-class pipeline citizen with an explicit economics layer: batched LLM
matching over `atlas_statements` (name + statement text + module context vs.
concept informal statements), emitting CANDIDATE alignment rows with full
evidence blobs (model, prompt hash, similarity features, cost) — **plus** a
measured promotion funnel: every batch records dollars spent, candidates
proposed, candidates promoted to ALIGNED, and candidates refuted. Cost per
confirmed alignment becomes a published, per-edition number.

**Why it compounds.** Alignment is the atlas's novel core and its scarcest
resource — the statement layer is ~10⁵–10⁶ rows and hand curation cannot
scale past the hundreds. LLM proposal is the only route to thousands of
alignments, and the tier system was designed precisely so machine guessing
can run hot without contaminating headline numbers. The economics layer is
what makes it *compound* rather than just run: measured precision-per-dollar
tells the pipeline which matching strategies to feed (name heuristics are
nearly free; full statement-text comparison costs tokens), and the
promote/refute record becomes training signal and — via proposal 5 — a
citable dataset (alignment prediction with human-adjudicated ground truth is
a genuinely novel ML benchmark).

**Mechanism.**
- `tools/propose_alignments.py`: candidate generation is two-stage to control
  cost — a free lexical/embedding prefilter (concept title vs. native name +
  module path) shortlists ≤K statements per concept, then one batched LLM
  call adjudicates the shortlist. Budget-capped per run (hard dollar ceiling
  in config, refuse-don't-degrade on exhaustion — the delta-gate philosophy
  applied to spend).
- Writes CANDIDATE rows only, via the existing transports; the ingest
  function grows a `candidate_insert` verb with the same batch caps.
  Evidence blob schema-validated like everything else.
- Promotion stays curation-as-code: a small review file format
  (`concepts/promotions/*.yaml` — candidate id, verdict ALIGNED/REFUTED,
  reviewer, note) synced by `sync_concepts.py`, so promotion provenance is
  git history, same as concepts. Refutations are kept, not deleted — they're
  the negative labels.
- Per-edition economics table in the release notes: proposed / promoted /
  refuted / $ spent / $ per promotion.

**Honest cost.** ~1 week to build; then a recurring LLM spend that the budget
cap makes a chosen number — start at $10–20 per weekly batch (thousands of
shortlist adjudications at batch pricing). The binding cost is **human review
time** for promotion: at even 30 seconds per candidate, 1,000 candidates is a
real backlog. The funnel metrics exist to keep proposal volume matched to
review capacity, not to maximize candidates.

**What could go wrong.** Three ways. (1) *Plausible-wrong at scale*: LLMs are
excellent at matching a theorem name to a similar-but-inequivalent statement
(different strength, added hypotheses); if reviewers rubber-stamp, ALIGNED
quality degrades exactly where the atlas's reputation lives. Defense:
promotion requires the reviewer to record *what they checked*, and spot-audit
a sample of promotions each edition. (2) *Un-reviewed candidate swamp*: the
UI must never let a wall of gray CANDIDATE chips visually read as coverage.
(3) *Prompt/model drift* silently changing proposal quality between batches —
the prompt hash in evidence exists so batches are comparable; treat a hash
change like a harvester version bump.

---

## 4. Atlas-driven prover objectives — the frontier as AutoLab target queue

**What.** Close the aim→prove segment: an exported, machine-readable target
queue (`targets.jsonl` per edition) drawn from the frontier view and the gap
list (proposal 2), consumed by the existing prover infrastructure — AutoLab
optimization runs, the Aristotle conveyor, EULER-style solver campaigns —
with a return path: a prover that lands a proof gets it into the Brockian
sanitized registry via the *existing* prove→AXLE-attest→registry path, and
the next brockian harvest picks it up automatically. The atlas never ingests
prover output directly.

**Why it compounds.** This is the whole loop, closed: the atlas *aims*
(frontier + gaps, honest selection made explicit per METHOD), provers
*prove*, AXLE *verifies*, the registry *remembers*, the harvester feeds the
atlas, and the next edition's frontier is measurably smaller — with the
shrinkage itself a published per-edition metric ("frontier delta"). It also
gives AutoLab something it currently lacks: an externally-grounded objective
function. "Targets closed per edition, weighted by rank" is a legible metric
to optimize solver configurations against, and every increment is a real
theorem, kernel-checked — no reward hacking surface, because the reward *is*
the verification.

**Mechanism.**
- `tools/build_targets.py`: emit frontier concepts + single-system gaps with
  formal-statement stubs where they exist (the 25 targets-board problems with
  Brockian formalized statements ship their statements; the rest ship
  informal text + a `needs_formal_statement` flag — statement formalization
  is itself a queue item, per the statement-fidelity discipline).
- Chris-gate on queue composition, consistent with the hyper-leverage
  program's standing rule: the frontier *queue* an engine consumes is an
  approved artifact, not a live feed. A `targets/APPROVED.yaml` in-repo marks
  which editions' queues are cleared for engine consumption.
- Return path is deliberately indirect: prover success → Brockian registry
  (existing AXLE attestation pipeline in brockian-mathematics) → sanitized
  `/verified-registry.json` → brockian harvester → atlas. One-way valve; the
  atlas's report-don't-verify rule survives untouched.
- Per-edition "frontier delta" in release notes: targets closed, by whom
  (which solver campaign), each linking the new registry entry.

**Honest cost.** Cheap on the atlas side (2–3 days: exporter, approval file,
release wiring). The real cost sits with the provers — solver compute
(AutoLab budget caps already exist; the SAIR-era $200-cap pattern applies)
and the human formalization time for `needs_formal_statement` targets, which
is the true bottleneck and should be stated as such in the queue.

**What could go wrong.** *Goodharting the frontier*: solvers will rationally
pick the easiest targets, so "frontier delta" can look healthy while nothing
hard moves — publish the rank-weighted and unweighted numbers side by side.
*Statement-fidelity failure at the entry point*: a mis-formalized target
stub means the prover proves the wrong theorem with a valid proof — the most
dangerous failure in the whole loop; target stubs must carry the same
tier/evidence discipline as alignments, and a proved target's alignment to
its concept still goes through normal review, not auto-ALIGNED. *Compute
burn*: an unattended solver campaign against a stale queue; the approval
gate and budget caps are the controls, and both must be defaults, not
options.

---

## 5. Editions as a citable research dataset — DOI, dataset card, benchmark tasks

**What.** Promote the weekly editions from "GitHub Releases we make" to a
first-class research dataset: a proper dataset card (composition, per-library
licenses, granularity caveats, known biases), archival deposit with a DOI
(Zenodo's GitHub integration mints one per release for near-zero effort), a
mirrored copy on Hugging Face datasets for the ML audience, and 2–3 defined
benchmark tasks with train/test splits — starting with **alignment
prediction** (given a concept and a candidate statement, predict
ALIGNED/REFUTED; ground truth from proposal 3's adjudicated promotion
records) and **cross-library retrieval** (given a statement in library A,
retrieve its counterpart in library B; ground truth from multi-system
CURATED alignments like the Wiedijk set).

**Why it compounds.** Credibility and distribution in one move. A DOI makes
the atlas citable in papers — every citation is an inbound edge to
riemannlab.com and to the Brockian corpus sitting as a peer library inside a
dataset ML researchers actually use. The benchmark tasks recruit outside
effort into the atlas's own bottleneck: every model built for alignment
prediction is a candidate proposer the pipeline can evaluate (on the
published test split) and potentially adopt, feeding proposal 3's economics.
And the discipline is nearly free: the pipeline already produces checksummed,
manifested, reproducible snapshots — the atlas was accidentally built to
dataset-release standards, so this move mostly *names* what already exists.

**Mechanism.**
- `DATASET-CARD.md` in-repo, rendered into each release: schema, per-library
  granularity table (statement vs. entry vs. package level — the naive-count
  trap from proposal 1, stated once, prominently), license matrix from
  `DATA-LICENSES.md`, tier semantics, and known limitations verbatim from
  METHOD.
- Enable Zenodo–GitHub integration on the repo → automatic DOI per edition,
  plus a concept DOI for the dataset as a whole. Add citation metadata
  (`CITATION.cff`).
- `tools/build_benchmarks.py`: derive task files from the DB at edition time;
  splits are frozen per edition and never resplit (temporal splits — train
  on edition ≤N, test on later adjudications — avoid leakage as the dataset
  grows). Hugging Face mirror is a small upload script in `edition.yml`.
- Benchmark ground truth uses only adjudicated records (CURATED alignments,
  reviewed promotions/refutations) — the headline rule extended to ML
  labels: CANDIDATE is never a label.

**Honest cost.** 3–5 days: dataset card, Zenodo/HF wiring, benchmark
derivation, plus a real one-time licensing pass (redistribution via HF must
respect the per-entry AFP rule already in `DATA-LICENSES.md` — metadata-only
keeps this tractable, but it must be checked, not assumed). Ongoing cost near
zero; it rides the existing edition workflow.

**What could go wrong.** *Premature launch*: a benchmark with 200 concepts
and a few hundred adjudications is a demo, not a benchmark — releasing it as
the latter would burn exactly the credibility the move exists to build. Gate
the benchmark announcement on a stated size threshold (e.g. ≥1,000
adjudicated alignment labels); ship the DOI and dataset card immediately, the
benchmark when it's real. *License exposure* on the HF mirror if any
statement text slips through from a restrictively-licensed AFP entry — the
mirror build must run the same license filter as releases, with a test.
*Split leakage* as later editions restate earlier data; the temporal-split
rule is the defense and belongs in the dataset card, not just the code.

---

## Sequencing

Dependency-honest order, not priority order — 2, 4, and 5(card+DOI) are
independently startable now:

1. **Now, cheap:** proposal 2 (gap mining — days, pure derivation) and
   proposal 5's dataset card + DOI (days, names what exists).
2. **Next, the big rock:** proposal 1 (AFP statement level) — it multiplies
   the value of everything else and should start before the alignment
   tooling scales.
3. **Then:** proposal 3 (LLM alignment with economics) once AFP statements
   give it a worthy search space, and proposal 4's target queue once the
   approval-file mechanism has an owner.
4. **Last to *announce*:** proposal 5's benchmark tasks, gated on the
   adjudicated-label threshold that proposal 3 generates.

Each proposal keeps the standing invariants: measured numbers only, CANDIDATE
never in headlines, retire-never-delete, stated coverage, and the atlas
reports — it does not re-check.

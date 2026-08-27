# The Proving Flywheel

> Operating doc for the loop specified in
> [`docs/2026-08-27-proving-flywheel-spec.md`](2026-08-27-proving-flywheel-spec.md).
> Architecture context: [`docs/PIPELINE.md`](PIPELINE.md).

One sentence: **frontier → nomination → (Chris gate) → campaign →
certificate landing in the brockian-mathematics registry → harvest →
CURATED alignment in the Atlas.**

---

## The two-frontiers rule

The concept index carries two seeds with *different* frontier meanings. The
nominator keeps them strictly separated and so must every human reading its
output:

| Frontier | Seed | What a campaign means |
|---|---|---|
| **Mathematical** | `seed_source: targets-board` | Genuinely open problems. Progress on a **named, certifiable sub-statement** — never "solve the conjecture". |
| **Formalization** | `seed_source: wiedijk100`, status `open` | *Proven* mathematics the Atlas has not yet recorded a verification for. **Coverage** work — find or produce the formalization. Never framed as open mathematics. |

Cross-seed duplicates (e.g. Fermat's Last Theorem on both seeds) are deduped
by normalized title: the mathematical-frontier row wins and the duplicate is
annotated on it, not listed twice.

## The four stages

### 1. Nominate — `tools/nominate_frontier.py`

Deterministic, read-only, runs every edition. Reads the seeds plus live
alignment counts (CANDIDATE tier never counted) and emits
`concepts/frontier-nominations.yaml` — a **proposal document only; the tool
never writes to the database**. Board problems whose `board_status` is
`resolved`, `disputed`, or `independent` are never nominated: they land in an
explicit `excluded:` section with the reason. Mathematical nominations are
tiered by a versioned, git-reviewed table (curation-as-code, no LLM):

- `ENGINE-READY` — the curated table names a finite sub-statement an engine
  can certify. Membership requires that named sub-statement; "instances are
  searchable" is not enough.
- `FORMALIZE-FIRST` — the first certifiable move is a precise formal
  statement in the Brockian registry (the 25 existing targets-board statement
  modules are the precedent, cited by `native_name` as evidence).
  `partially-formalized` ranks above `open`: its first move is already done.
- `NOT-ATTACKABLE-YET` — the honest bucket (Hodge, Navier–Stokes,
  Yang–Mills), rendered as prominently as the others.

### 2. Approve — the Chris gate

Approvals are hand-recorded in `concepts/campaign-approvals.yaml` — a
separate, never-regenerated artifact, so regenerating nominations can never
clobber an approval. **No engine consumes budget without an entry there.**
Git history is the audit trail.

### 3. Campaign — budgeted, engine-dispatched

Each approved nomination gets a campaign brief (template below) naming the
exact sub-statement, the engine, the verifier, the budget cap, and the
success criterion. Dispatch is manual in v0.

### 4. Certify and return — the registry is the sole return path

Success means **landing in the brockian-mathematics registry** under its
existing PROVED / axioms_ok / sorry_free gates. An AXLE-attested certificate
that does not land in the registry does **not** return to the Atlas — every
brief states this. From the registry, the existing rails carry the result:
harvester → `atlas_statements` → `concepts/sync_concepts.py`, whose
module-prefix resolver closes the last gap (board alignments name Lean
*modules*; the harvester emits *declarations* — the resolver matches
`<module>.` prefixes deterministically and records
`resolution: module-prefix` in the alignment evidence).

## Status promotion is curation, not automation

No stage of this loop mutates concept status. Promotion
(`open → partially-formalized → formalized`) remains a **recorded curation
act in the seed YAML** — `formalized` is a human judgment, not a script
output. An alignment claims formalization-of-statement; proof status lives on
the statement row, never on the alignment.

---

## Campaign brief template

```markdown
# Campaign brief: <concept slug>

- **Nomination**: <slug> (frontier-nominations.yaml, generated <date>)
- **Approval**: entry in concepts/campaign-approvals.yaml, dated <date>
- **Exact sub-statement**: <the precise, finite, certifiable claim — bounds
  and encodings stated explicitly; part of the claim, not a footnote>
- **Engine**: <AutoLab project / Aristotle batch / Brockian pipeline>
- **Verifier**: <AXLE / lake build / official judge — the thing that judges
  success; the engine never grades itself>
- **Budget cap**: <hard spend cap>
- **Success criterion**: a machine-checked certificate, never a claim.
  Success = the result lands in the brockian-mathematics registry under its
  PROVED/axioms_ok/sorry_free gates. An attested certificate that does not
  land in the registry does NOT return to the Atlas.
```

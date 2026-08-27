"""Build the targets-board concept seed from the Riemann Lab /targets board.

Upstream shape (observed 2026-08-27, src/data/top100-problems.json in the
riemannlab Lovable project, board snapshot as_of 2026-08-06): a JSON object
with `meta` (as_of, counts, disclaimer) and `problems`, each problem a mapping
with `id`, `name`, `field`, `statement`, `status` (open / resolved / disputed /
independent), `prize`, `brockian` (Lean module name in the Brockian corpus, or
null), `resolved`, `note`. The committed fixture tests/fixtures/targets_board.json
is a verbatim copy of that file.

Honesty rules:
- `brockian` on the board means the STATEMENT is formalized (AXLE-verified to
  typecheck) — never a proof. Any brockian reference yields atlas status
  "partially-formalized"; everything else stays "open".
- Counts are measured from the problems array, never read from `meta`.
- The board's own lifecycle status (resolved-by-others / disputed /
  independent) is preserved verbatim as `board_status` so the atlas never
  silently rebrands a resolved-by-others problem as open mathematics.
- Note: board `brockian` values are Lean MODULE names (e.g.
  "Brockian.GoldbachComb"), not declaration names; exact native_name matching
  against harvested statements will report these alignments PENDING until they
  are resolved at module granularity.
"""

import argparse
import json
import re


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _load_source(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        import requests

        resp = requests.get(source, timeout=30)
        resp.raise_for_status()
        return resp.json()
    with open(source, encoding="utf-8") as f:
        return json.load(f)


def build_seed(source: str, out: str) -> dict:
    import yaml

    raw = _load_source(source)
    problems = raw.get("problems")
    if not isinstance(problems, list):
        raise ValueError("board data missing 'problems' list")
    meta = raw.get("meta") or {}

    concepts = []
    for position, p in enumerate(problems, start=1):
        brockian = p.get("brockian")
        alignments = []
        if isinstance(brockian, str) and brockian.strip():
            alignments.append(
                {
                    "library": "brockian",
                    "native_name": brockian.strip(),
                    "tier": "CURATED",
                    "evidence": {"source": "riemannlab targets board"},
                }
            )
        statement = p.get("statement")
        if not (isinstance(statement, str) and statement.strip()):
            statement = None  # board has no statement text → null, never invented
        concepts.append(
            {
                "slug": f"target-{position:03d}-" + _slugify(p["name"]),
                "title": p["name"],
                "informal_statement": statement,
                "msc_primary": None,
                "status": "partially-formalized" if alignments else "open",
                # Board provenance, preserved verbatim (extra keys are ignored
                # by concepts/sync_concepts.py but keep the seed honest):
                "board_id": p["id"],
                "board_status": p.get("status"),
                "alignments": alignments,
            }
        )

    slugs = [c["slug"] for c in concepts]
    if len(slugs) != len(set(slugs)):
        dupes = sorted({s for s in slugs if slugs.count(s) > 1})
        raise ValueError(f"duplicate slugs generated: {dupes}")

    doc = {
        "seed_source": "targets-board",
        "generated_from": (
            "riemannlab /targets board (src/data/top100-problems.json, "
            f"as_of {meta.get('as_of', 'unknown')})"
        ),
        "concepts": concepts,
    }
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
    return doc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True,
                        help="path or URL to the board JSON (top100-problems.json)")
    parser.add_argument("--out", required=True, help="output seed YAML path")
    args = parser.parse_args()
    doc = build_seed(source=args.source, out=args.out)
    aligned = sum(1 for c in doc["concepts"] if c["alignments"])
    print(f"wrote {args.out}: {len(doc['concepts'])} concepts, "
          f"{aligned} with brockian statement-level alignments (measured)")


if __name__ == "__main__":
    main()

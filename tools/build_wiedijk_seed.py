"""Build the Wiedijk-100 concept seed from mathlib4's docs/100.yaml.

Upstream shape (observed 2026-08-26): a YAML mapping keyed by theorem number
(int), each entry a mapping with `title` and, where formalized in mathlib,
either `decl` (single declaration name) or `decls` (list of names). Entries
with neither are unformalized in mathlib. Extra fields (`authors`, `links`,
`note`, `statement`, ...) are tolerated and ignored.

v0 never claims "formalized" — any mathlib alignment yields
"partially-formalized"; promotion is a curation judgment.
"""

import argparse
import re

import yaml


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _load_source(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        import requests

        resp = requests.get(source, timeout=30)
        resp.raise_for_status()
        return yaml.safe_load(resp.text)
    with open(source, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_seed(source: str, out: str) -> dict:
    raw = _load_source(source)
    concepts = []
    for key, entry in raw.items():
        num = int(key)
        title = entry["title"]
        alignments = []
        if "decl" in entry:
            names, field = [entry["decl"]], "decl"
        elif "decls" in entry:
            if not isinstance(entry["decls"], list):
                raise ValueError(f"entry {num}: decls must be a list")
            names, field = list(entry["decls"]), "decls"
        else:
            names, field = [], None
        # Drop non-string/blank names; a field present but all-filtered means
        # no alignment (status stays open).
        names = [n for n in names if isinstance(n, str) and n.strip()]
        for name in names:
            alignments.append(
                {
                    "library": "mathlib",
                    "native_name": name,
                    "tier": "CURATED",
                    "evidence": {"source": "mathlib4 docs/100.yaml", "field": field},
                }
            )
        concepts.append(
            {
                "slug": f"wiedijk-{num:03d}-" + _slugify(title),
                "title": title,
                "wiedijk_number": num,
                "informal_statement": None,  # never auto-filled
                "msc_primary": None,
                "status": "partially-formalized" if alignments else "open",
                "alignments": alignments,
            }
        )
    concepts.sort(key=lambda c: c["wiedijk_number"])
    doc = {
        "seed_source": "wiedijk100",
        "generated_from": "mathlib4 docs/100.yaml",
        "concepts": concepts,
    }
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
    return doc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True, help="path or URL to docs/100.yaml")
    parser.add_argument("--out", required=True, help="output seed YAML path")
    args = parser.parse_args()
    doc = build_seed(source=args.source, out=args.out)
    aligned = sum(1 for c in doc["concepts"] if c["alignments"])
    print(f"wrote {args.out}: {len(doc['concepts'])} concepts, {aligned} with mathlib alignments")


if __name__ == "__main__":
    main()

"""Mathlib harvester — reads the doc-gen4 declaration export.

Probe evidence (2026-08-26, ranged-byte probes only, full file never downloaded):
  URL: https://leanprover-community.github.io/mathlib4_docs/declarations/declaration-data.bmp
       HTTP 200, content-length 66,895,626 (~67 MB). Content-type claims image/bmp
       but the payload is JSON (doc-gen4 ships it with a .bmp extension).
  Shape: {"declarations": {"<Fully.Qualified.Name>": {"docLink": "...", "kind": "..."}}}
    - docLink: relative page+anchor, e.g.
      "./Mathlib/NumberTheory/ADEInequality.html#ADEInequality.A"
      -> module = dotted path of the .html page (Mathlib.NumberTheory.ADEInequality)
      -> source_url = DOCS_BASE + docLink (module page + #name anchor)
    - kind values observed in first 400 KB: theorem (2031), def (437),
      instance (372), ctor (44), class (21), structure (19), inductive (3)
    - No statement text / docstring in this export -> statement_text is None.
"""
import argparse
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from atlas.emit import write_harvest

DEFAULT_SOURCE = ("https://leanprover-community.github.io/mathlib4_docs/"
                  "declarations/declaration-data.bmp")
DOCS_BASE = "https://leanprover-community.github.io/mathlib4_docs/"
HARVESTER_VERSION = "0.1.0"
_KINDS = {"theorem": "theorem", "thm": "theorem",
          "def": "definition", "definition": "definition",
          "structure": "definition", "instance": "definition"}


def _load(source):
    """Return (parsed json, source_version) — version from ETag/Last-Modified
    for URLs (per-run provenance), file name for local fixtures."""
    if source.startswith("http"):
        import requests
        r = requests.get(source, timeout=600)
        r.raise_for_status()
        ver = r.headers.get("ETag") or r.headers.get("Last-Modified") or "unknown"
        return r.json(), ver
    return json.loads(pathlib.Path(source).read_text()), pathlib.Path(source).name


def to_statement(name, decl):
    doc_link = decl["docLink"]
    page, _, anchor = doc_link.partition("#")
    module = page.lstrip("./").removesuffix(".html").replace("/", ".")
    source_url = DOCS_BASE + page.lstrip("./")
    if anchor:
        # mathlib names routinely contain unicode (subscripts etc.) — encode.
        source_url += "#" + urllib.parse.quote(anchor)
    return {
        "library": "mathlib",
        "native_name": name,
        "kind": _KINDS.get(str(decl.get("kind", "")).lower(), "other"),
        "statement_text": None,  # doc-gen4 declaration export carries no statement text
        "module": module or None,
        "source_url": source_url,
        "subject_codes": [],
    }


def harvest(source=DEFAULT_SOURCE, out_dir="out/mathlib"):
    data, src_ver = _load(source)
    decls = data["declarations"]
    rows = []
    skipped = 0
    for name, decl in decls.items():
        if not decl.get("docLink"):
            skipped += 1
            continue
        rows.append(to_statement(name, decl))
    print(f"skipped {skipped} entries without docLink", file=sys.stderr)
    return write_harvest(out_dir, "mathlib", rows,
                         harvester_version=HARVESTER_VERSION,
                         source_version=src_ver,
                         subject_derivation="Mathlib module path prefix")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default="out/mathlib")
    a = ap.parse_args()
    print(json.dumps(harvest(source=a.source, out_dir=a.out), indent=2))

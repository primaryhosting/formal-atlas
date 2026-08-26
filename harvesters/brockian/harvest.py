"""Brockian harvester — reads ONLY the prover-owned sanitized public registry.

Inclusion rule (the library's own checked status, per METHOD.md): register PROVED,
axioms_ok, sorry_free. Everything else is not machine-verified mathematics and is
not the atlas's to report.
"""
import argparse
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from atlas.emit import write_harvest

DEFAULT_SOURCE = "https://torus.riemannlab.com/verified-registry.json"
HARVESTER_VERSION = "0.1.0"
_KINDS = {"theorem": "theorem", "lemma": "lemma", "def": "definition",
          "definition": "definition", "axiom": "axiom"}


def _load(source):
    if source.startswith("http"):
        import requests
        r = requests.get(source, timeout=120)
        r.raise_for_status()
        return r.json()
    return json.loads(pathlib.Path(source).read_text())


def to_statement(entry):
    return {
        "library": "brockian",
        "native_name": entry["name"],
        "kind": _KINDS.get(str(entry.get("kind", "")).lower(), "other"),
        "statement_text": entry.get("statement") or None,
        "module": entry.get("module") or None,
        "source_url": "https://torus.riemannlab.com/explore/lean-registry?name="
                      + urllib.parse.quote(entry["name"]),
        "subject_codes": [],
    }


def harvest(source=DEFAULT_SOURCE, out_dir="out/brockian"):
    data = _load(source)
    if data.get("schema") != "brockian-public-verified-registry/v1":
        raise SystemExit(f"unexpected registry schema: {data.get('schema')!r}")
    rows = [to_statement(e) for e in data["theorems"]
            if e.get("register") == "PROVED" and e.get("axioms_ok") and e.get("sorry_free")]
    return write_harvest(out_dir, "brockian", rows,
                         harvester_version=HARVESTER_VERSION,
                         source_version=data.get("schema", "unknown"),
                         subject_derivation="module prefix (not yet mapped to MSC)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default="out/brockian")
    a = ap.parse_args()
    print(json.dumps(harvest(source=a.source, out_dir=a.out), indent=2))

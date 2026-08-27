"""Coq/Rocq harvester — PACKAGE-LEVEL: one row per opam package, not per theorem.

Coq has no single machine-readable index of individual theorems across all
packages, so per the spec this harvester covers the *package* granularity only.
Coverage honesty: rows describe opam packages in the "released" Coq opam
repository; kind is "other" and statement_text is the package synopsis.

Probe evidence (2026-08-27, index fully downloaded — 749 KB, under local limit):
  URL chain: https://coq.inria.fr/opam/released/ -> 301 https://rocq-prover.org/opam/released
             index.tar.gz -> 302 https://rocq-prover.github.io/opam/released/index.tar.gz
             (HTTP 200, content-type application/gzip, content-length 749,211)
  Archive layout (opam 2.0 repository index):
    version                                   -> "0.9.0"
    repo                                      -> opam-version / browse / upstream / stamp
      stamp: "2026-08-27 07:43"               -> used as source_version
      upstream: "https://github.com/rocq-prover/opam/tree/master/released"
    packages/<name>/<name>.<version>/opam     -> 3,584 opam files across 586 packages
  opam synopsis layouts observed in the real index (all handled):
    synopsis: "one line"                      (common)
    synopsis:     "extra spaces"              (coq-geocoq)
    synopsis:\n  "value on the next line"     (coq-sail 0.20.2)
  Every opam file in the 2026-08-27 snapshot has a synopsis; absence still
  yields statement_text = None rather than a crash.
"""
import argparse
import json
import pathlib
import re
import sys
import tarfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from atlas.emit import write_harvest

DEFAULT_SOURCE = "https://rocq-prover.org/opam/released/index.tar.gz"
PACKAGE_URL_BASE = "https://github.com/rocq-prover/opam/tree/master/released/packages/"
HARVESTER_VERSION = "0.1.0"

_MEMBER_RE = re.compile(r"^packages/([^/]+)/\1\.([^/]+)/opam$")
_SYNOPSIS_RE = re.compile(r'^synopsis:\s*"((?:[^"\\]|\\.)*)"', re.M)
_STAMP_RE = re.compile(r'^stamp:\s*"([^"]*)"', re.M)


def _compare_versions(a, b):
    """opam (Debian-style) version comparison: alternate non-digit/digit parts;
    '~' sorts before everything (including end-of-string), digits compare
    numerically. Returns <0, 0, >0. Enough for the version strings in the
    released repo (no epochs observed)."""
    def _char_order(c):
        if c == "~":
            return -1
        if c.isalpha():
            return ord(c)
        return ord(c) + 0x10000  # non-letters sort after letters
    ia = ib = 0
    while ia < len(a) or ib < len(b):
        while True:  # non-digit run (empty run == order 0, between '~' and letters)
            ca = a[ia] if ia < len(a) and not a[ia].isdigit() else None
            cb = b[ib] if ib < len(b) and not b[ib].isdigit() else None
            if ca is None and cb is None:
                break
            oa = _char_order(ca) if ca is not None else 0
            ob = _char_order(cb) if cb is not None else 0
            if oa != ob:
                return oa - ob
            ia += 1
            ib += 1
        na = 0
        while ia < len(a) and a[ia].isdigit():
            na = na * 10 + int(a[ia])
            ia += 1
        nb = 0
        while ib < len(b) and b[ib].isdigit():
            nb = nb * 10 + int(b[ib])
            ib += 1
        if na != nb:
            return na - nb
    return 0


def _parse_synopsis(opam_text):
    """Extract the synopsis string from opam file text, or None if absent."""
    m = _SYNOPSIS_RE.search(opam_text)
    if not m:
        return None
    # minimal opam string unescaping (only \" and \\ occur in practice)
    return re.sub(r'\\(.)', r'\1', m.group(1))


def _fetch(source):
    """Return a local path to the index tarball (downloading if source is a URL)."""
    if source.startswith("http"):
        import tempfile

        import requests
        r = requests.get(source, timeout=600)
        r.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
        tmp.write(r.content)
        tmp.close()
        return pathlib.Path(tmp.name)
    return pathlib.Path(source)


def harvest(source=DEFAULT_SOURCE, out_dir="out/coq"):
    path = _fetch(source)
    latest = {}  # package -> (version, member)
    source_version = "unknown"
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name == "repo":
                m = _STAMP_RE.search(tar.extractfile(member).read().decode("utf-8"))
                if m:
                    source_version = m.group(1)
                continue
            m = _MEMBER_RE.match(member.name)
            if not m:
                continue
            pkg, ver = m.group(1), m.group(2)
            if pkg not in latest or _compare_versions(ver, latest[pkg][0]) > 0:
                latest[pkg] = (ver, member)
        rows = []
        for pkg, (_ver, member) in latest.items():
            text = tar.extractfile(member).read().decode("utf-8")
            rows.append({
                "library": "coq",
                "native_name": pkg,
                "kind": "other",  # package-level rows, not individual theorems
                "statement_text": _parse_synopsis(text),
                "module": None,
                "source_url": PACKAGE_URL_BASE + pkg,
                "subject_codes": [],
            })
    return write_harvest(
        out_dir, "coq", rows,
        harvester_version=HARVESTER_VERSION,
        source_version=source_version,
        subject_derivation=None)  # no subject taxonomy at package granularity


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default="out/coq")
    a = ap.parse_args()
    print(json.dumps(harvest(source=a.source, out_dir=a.out), indent=2))

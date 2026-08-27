"""AFP harvester — entry-level (per the atlas spec: entry metadata first,
statement-level later).

Source is the machine-readable site index https://isa-afp.org/entries/index.json
(~1.3 MB, 1,025 entries as of 2026-08-26; served with ETag + Last-Modified).
It is the same JSON the AFP site's own FlexSearch UI fetches, so it tracks the
published archive exactly. Fields per entry: shortname, title, topics,
topic_links, authors, date, year, abstract, link, permalink, related.

One statement row is emitted PER ENTRY (kind "other" — an AFP entry is a whole
development, not a single theorem). statement_text carries the entry title.
Topic tags go to module (first tag) and subject_codes (all tags), which is what
subject_derivation="AFP topic tags" claims — these are AFP's own taxonomy
strings (e.g. "Mathematics/Analysis"), NOT MSC codes.

Known limitation (honesty note): per-entry LICENSE is not present in this
index. It lives in the devel repo's metadata/entries/<name>.toml (one file per
entry) and on each entry's HTML page; harvesting it would need ~1,000 extra
requests, so it is deliberately out of scope for the entry-level harvest.
AFP-wide licensing is BSD-3-Clause or LGPL, chosen per entry.
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from atlas.emit import write_harvest

DEFAULT_SOURCE = "https://isa-afp.org/entries/index.json"
HARVESTER_VERSION = "0.1.0"


def parse_entries(data):
    if not isinstance(data, list):
        raise ValueError("AFP entries index: expected a JSON array of entry objects")
    for e in data:
        name = e.get("shortname") if isinstance(e, dict) else None
        if not name:
            raise ValueError(f"AFP entry missing shortname: {json.dumps(e)[:200]}")
        topics = [t for t in (e.get("topics") or []) if isinstance(t, str) and t]
        yield {
            "library": "afp",
            "native_name": name,
            "kind": "other",
            "statement_text": e.get("title") or None,
            "module": topics[0] if topics else None,
            # Constructed per spec; the index's own permalink is the same page
            # on the apex domain (https://isa-afp.org/entries/<name>.html).
            "source_url": f"https://www.isa-afp.org/entries/{name}.html",
            "subject_codes": topics,
        }


def harvest(source=DEFAULT_SOURCE, out_dir="out/afp"):
    if source.startswith("http"):
        import requests
        r = requests.get(source, timeout=120)
        r.raise_for_status()
        data = r.json()
        src_ver = r.headers.get("ETag") or r.headers.get("Last-Modified") or "unknown"
    else:
        data = json.loads(pathlib.Path(source).read_text())
        src_ver = pathlib.Path(source).name
    rows = list(parse_entries(data))
    return write_harvest(out_dir, "afp", rows,
                         harvester_version=HARVESTER_VERSION, source_version=src_ver,
                         subject_derivation="AFP topic tags")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default="out/afp")
    a = ap.parse_args()
    print(json.dumps(harvest(source=a.source, out_dir=a.out), indent=2))

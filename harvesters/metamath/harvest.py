"""Metamath harvester — streams set.mm, emits $a/$p labels with section context."""
import argparse, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from atlas.emit import write_harvest

DEFAULT_SOURCE = "https://raw.githubusercontent.com/metamath/set.mm/develop/set.mm"
HARVESTER_VERSION = "0.1.0"
_STMT = re.compile(r"^\s*(\S+)\s+\$([ap])\s+(.*)$")


def parse_mm(lines):
    section = None
    in_comment = False
    comment_buf = []
    pending = None  # (label, kind_char, math_parts)
    for raw in lines:
        line = raw.rstrip("\n")
        # Statement match takes precedence over comment detection: a trailing
        # same-line comment (`foo $a x $. $( note $)`) must not swallow the
        # statement. Only a line that BEGINS a comment enters comment mode.
        if pending is None and line.lstrip().startswith("$("):
            in_comment = True
            comment_buf = []
        if in_comment:
            comment_buf.append(line)
            if "$)" in line:
                in_comment = False
                block = "\n".join(comment_buf)
                if "#*#*" in block:
                    for cand in block.splitlines():
                        t = cand.strip().strip("$()").strip()
                        if t and "#*" not in t:
                            section = t
                            break
            continue
        if pending is not None:
            label, kc, parts = pending
            end = line.split("$=")[0].split("$.")[0]
            parts.append(end)
            if "$=" in line or "$." in line:
                yield _row(label, kc, " ".join(" ".join(parts).split()), section)
                pending = None
            continue
        m = _STMT.match(line)
        if m:
            label, kc, rest = m.group(1), m.group(2), m.group(3)
            head = rest.split("$=")[0].split("$.")[0]
            if "$=" in rest or "$." in rest:
                yield _row(label, kc, " ".join(head.split()), section)
            else:
                pending = (label, kc, [head])


def _row(label, kind_char, math, section):
    if kind_char == "p":
        kind = "theorem"
    elif label.startswith("ax-"):
        kind = "axiom"
    elif label.startswith("df-"):
        kind = "definition"
    else:
        kind = "axiom"
    return {"library": "metamath", "native_name": label, "kind": kind,
            "statement_text": math or None, "module": section,
            "source_url": f"https://us.metamath.org/mpeuni/{label}.html",
            "subject_codes": []}


def harvest(source=DEFAULT_SOURCE, out_dir="out/metamath"):
    if source.startswith("http"):
        import requests
        r = requests.get(source, stream=True, timeout=300)
        r.raise_for_status()
        rows = list(parse_mm(l.decode("utf-8", "replace") for l in r.iter_lines()))
        src_ver = r.headers.get("ETag") or r.headers.get("Last-Modified") or "unknown"
    else:
        rows = list(parse_mm(pathlib.Path(source).read_text().splitlines()))
        src_ver = pathlib.Path(source).name
    return write_harvest(out_dir, "metamath", rows,
                         harvester_version=HARVESTER_VERSION, source_version=src_ver,
                         subject_derivation="set.mm chapter headers")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default="out/metamath")
    a = ap.parse_args()
    print(json.dumps(harvest(source=a.source, out_dir=a.out), indent=2))

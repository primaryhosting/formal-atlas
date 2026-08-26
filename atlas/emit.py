"""Single writer for harvester output: validated statements.jsonl + manifest.json.

Every harvester calls write_harvest(); nothing else writes these files. Validation
here is the schema gate the spec's CI requires — a harvester emitting garbage
fails loudly at emit time, not at load time.
"""
import datetime as _dt
import hashlib
import json
import pathlib

import jsonschema

_SCHEMA_DIR = pathlib.Path(__file__).resolve().parent.parent / "schema"
_STMT_SCHEMA = json.loads((_SCHEMA_DIR / "statement.schema.json").read_text())
_MAN_SCHEMA = json.loads((_SCHEMA_DIR / "manifest.schema.json").read_text())


def write_harvest(out_dir, library, statements, *, harvester_version, source_version,
                  subject_derivation=None):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    validator = jsonschema.Draft202012Validator(_STMT_SCHEMA)
    seen = set()
    lines = []
    for s in statements:
        validator.validate(s)
        if s["library"] != library:
            raise ValueError(f"statement library {s['library']!r} != harvest library {library!r}")
        if s["native_name"] in seen:
            raise ValueError(f"duplicate native_name: {s['native_name']}")
        seen.add(s["native_name"])
        lines.append(json.dumps(s, ensure_ascii=False, sort_keys=True))
    blob = ("\n".join(lines) + "\n") if lines else ""
    (out_dir / "statements.jsonl").write_text(blob, encoding="utf-8")
    manifest = {
        "library": library,
        "harvester_version": harvester_version,
        "source_version": source_version,
        "statement_count": len(lines),
        "harvested_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        "subject_derivation": subject_derivation,
    }
    jsonschema.Draft202012Validator(_MAN_SCHEMA).validate(manifest)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

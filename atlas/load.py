"""Load harvested output into Supabase (PostgREST).

Safety model: plan_upsert() is a pure function computing the upsert/retire plan
with two gates — refuse to retire an entire library on an empty harvest, and
refuse a >±20% statement-count swing without an explicit override. All network
side effects live in load(); tests exercise only the pure planning layer.

House pattern: every PostgREST request sends BOTH `apikey` and
`Authorization: Bearer` headers. These helpers (headers/get_paged/post/patch)
are the single HTTP layer — sync_concepts.py and edition.py import them
rather than duplicating header/pagination code.
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.parse

import requests

PAGE_SIZE = 1000
UPSERT_BATCH = 500
RETIRE_BATCH = 100


# ---------------------------------------------------------------- HTTP layer

def headers(service_key, **extra):
    h = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    h.update(extra)
    return h


def get_paged(supabase_url, service_key, path_query):
    """GET {url}/rest/v1/{path_query} with unconditional Range pagination.

    PostgREST caps single responses server-side; a one-shot read silently
    truncates. Loops until a page returns fewer than PAGE_SIZE rows.
    """
    rows = []
    i = 0
    while True:
        r = requests.get(
            f"{supabase_url}/rest/v1/{path_query}",
            headers=headers(service_key,
                            **{"Range-Unit": "items",
                               "Range": f"{i}-{i + PAGE_SIZE - 1}"}),
            timeout=120,
        )
        r.raise_for_status()
        page = r.json()
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        i += PAGE_SIZE


def post(supabase_url, service_key, path_query, body, *, prefer=None):
    extra = {"Content-Type": "application/json"}
    if prefer:
        extra["Prefer"] = prefer
    r = requests.post(f"{supabase_url}/rest/v1/{path_query}",
                      headers=headers(service_key, **extra),
                      data=json.dumps(body), timeout=120)
    r.raise_for_status()
    return r


def patch(supabase_url, service_key, path_query, body):
    r = requests.patch(f"{supabase_url}/rest/v1/{path_query}",
                       headers=headers(service_key,
                                       **{"Content-Type": "application/json"}),
                       data=json.dumps(body), timeout=120)
    r.raise_for_status()
    return r


def require_env():
    url = os.environ.get("ATLAS_SUPABASE_URL")
    key = os.environ.get("ATLAS_SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("error: ATLAS_SUPABASE_URL and ATLAS_SUPABASE_SERVICE_KEY "
                 "must be set in the environment")
    return url.rstrip("/"), key


# ------------------------------------------------------------- pure planning

def plan_upsert(existing_names, rows, allow_big_delta=False):
    """Compute the upsert/retire plan. Pure — no I/O.

    existing_names: set of native_name currently live in the DB for this library.
    rows: harvested statement dicts (each with native_name).
    """
    existing_names = set(existing_names)
    if not rows and existing_names:
        raise ValueError("refusing to retire entire library on empty harvest")
    if existing_names:
        delta = abs(len(rows) - len(existing_names)) / len(existing_names)
        if delta > 0.20 and not allow_big_delta:
            raise ValueError(
                f"count delta {delta:.0%} exceeds ±20% gate — re-run with "
                "--allow-big-delta after manual review")
    harvested_names = {r["native_name"] for r in rows}
    return {"retire": existing_names - harvested_names,
            "upsert_count": len(rows)}


# ------------------------------------------------------------- side effects

def _quote_name(name):
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def load(out_dir, supabase_url, service_key, allow_big_delta=False):
    out_dir = pathlib.Path(out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text())
    lib = manifest["library"]
    rows = [json.loads(line) for line in
            (out_dir / "statements.jsonl").read_text().splitlines() if line]

    try:
        # 1. existing names (paginated — never a one-shot read)
        existing = {r["native_name"] for r in get_paged(
            supabase_url, service_key,
            f"atlas_statements?library_id=eq.{lib}"
            "&select=native_name&order=native_name")}

        # 2. plan
        plan = plan_upsert(existing, rows, allow_big_delta)

        # 3. upsert in batches; retired=False on EVERY row so reappearing
        #    statements un-retire (merge-duplicates keeps omitted columns)
        payload = [{
            "library_id": r["library"],
            "native_name": r["native_name"],
            "kind": r["kind"],
            "statement_text": r.get("statement_text"),
            "module": r.get("module"),
            "source_url": r["source_url"],
            "subject_codes": r.get("subject_codes", []),
            "retired": False,
        } for r in rows]
        for i in range(0, len(payload), UPSERT_BATCH):
            post(supabase_url, service_key,
                 "atlas_statements?on_conflict=library_id,native_name",
                 payload[i:i + UPSERT_BATCH],
                 prefer="resolution=merge-duplicates,return=minimal")

        # 4. retire vanished statements (library_id filter MANDATORY)
        retire = sorted(plan["retire"])
        for i in range(0, len(retire), RETIRE_BATCH):
            joined = ",".join(_quote_name(n) for n in retire[i:i + RETIRE_BATCH])
            quoted = urllib.parse.quote(f"in.({joined})", safe="")
            patch(supabase_url, service_key,
                  f"atlas_statements?library_id=eq.{lib}&native_name={quoted}",
                  {"retired": True})

        # 5. library bookkeeping
        patch(supabase_url, service_key,
              f"atlas_libraries?id=eq.{lib}",
              {"statement_count": manifest["statement_count"],
               "last_harvest_at": manifest["harvested_at"],
               "harvester_version": manifest["harvester_version"]})
    except Exception:
        post(supabase_url, service_key, "atlas_harvest_runs",
             {"library_id": lib,
              "source_version": manifest.get("source_version"),
              "status": "failed"})
        raise

    # 6. record the successful run
    post(supabase_url, service_key, "atlas_harvest_runs",
         {"library_id": lib,
          "source_version": manifest["source_version"],
          "statements_seen": len(rows),
          "added": plan["upsert_count"],
          "retired": len(plan["retire"]),
          "status": "ok"})
    return plan


def record_failure(library, note, supabase_url, service_key):
    post(supabase_url, service_key, "atlas_harvest_runs",
         {"library_id": library, "status": "failed",
          "log_url": None, "source_version": note})


# ---------------------------------------------------------------------- CLI

def main():
    parser = argparse.ArgumentParser(
        description="Load a harvest output directory into Supabase")
    parser.add_argument("--dir", help="harvest output dir (statements.jsonl + manifest.json)")
    parser.add_argument("--allow-big-delta", action="store_true",
                        help="override the ±20% count-delta gate")
    parser.add_argument("--record-failure", metavar="LIB",
                        help="record a failed harvest run for LIB and exit")
    parser.add_argument("--note", default="", help="note for --record-failure")
    args = parser.parse_args()

    supabase_url, service_key = require_env()
    allow_big = args.allow_big_delta or os.environ.get("ATLAS_ALLOW_BIG_DELTA") == "1"

    if args.record_failure:
        record_failure(args.record_failure, args.note, supabase_url, service_key)
        print(f"recorded failed run for {args.record_failure}")
        return
    if not args.dir:
        parser.error("--dir is required unless --record-failure is given")
    plan = load(args.dir, supabase_url, service_key, allow_big_delta=allow_big)
    print(f"loaded {args.dir}: upserted {plan['upsert_count']}, "
          f"retired {len(plan['retire'])}")


if __name__ == "__main__":
    main()

"""Stamp an edition number onto live statements and harvest runs.

Run after a weekly release: `python -m atlas.edition --tag N`.

(a) last_seen_edition = N on every live (retired=false) row — unconditional.
    Deliberately NO `neq` guard: PostgREST `neq` excludes NULLs, and rows
    start with last_seen_edition NULL, so a neq filter would no-op forever.
(b) first_seen_edition = N where it is still NULL (first edition the row
    appeared in).
(c) edition_tag = N on ok harvest runs not yet stamped.

In ingest mode (ATLAS_INGEST_URL + ATLAS_INGEST_TOKEN) the atlas-ingest edge
function's {"action": "edition", "tag": N} performs all three stamps
server-side in place of the three PATCHes.

HTTP layer imported from atlas.load — no duplication.
"""
import argparse

from atlas.load import ingest_call, patch, require_transport


def stamp_edition(tag, supabase_url=None, service_key=None,
                  *, ingest_url=None, ingest_token=None):
    if ingest_url and ingest_token:
        ingest_call(ingest_url, ingest_token, {"action": "edition", "tag": tag})
        return
    patch(supabase_url, service_key,
          "atlas_statements?retired=eq.false",
          {"last_seen_edition": tag})
    patch(supabase_url, service_key,
          "atlas_statements?first_seen_edition=is.null",
          {"first_seen_edition": tag})
    patch(supabase_url, service_key,
          "atlas_harvest_runs?edition_tag=is.null&status=eq.ok",
          {"edition_tag": tag})


def main():
    parser = argparse.ArgumentParser(description="Stamp edition N onto the atlas")
    parser.add_argument("--tag", type=int, required=True, help="edition number")
    args = parser.parse_args()
    supabase_url, service_key, ingest_url, ingest_token = require_transport()
    stamp_edition(args.tag, supabase_url, service_key,
                  ingest_url=ingest_url, ingest_token=ingest_token)
    print(f"stamped edition {args.tag}")


if __name__ == "__main__":
    main()

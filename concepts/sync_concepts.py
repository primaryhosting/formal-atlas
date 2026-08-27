"""Sync concept seed YAMLs (concepts/*.yaml) into Supabase.

Upserts every concept into atlas_concepts, then resolves each alignment's
native_name against harvested atlas_statements. Alignments whose statement
has not been harvested yet are reported as PENDING and skipped — never an
error, because mathlib alignments only resolve after the first mathlib
harvest. Re-running is idempotent.

HTTP layer (headers, pagination, raise_for_status) is imported from
atlas.load — single implementation, no duplication.
"""
import os
import pathlib
import sys
import urllib.parse

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.load import get_paged, post, require_env

CONCEPTS_DIR = pathlib.Path(__file__).resolve().parent


def _concept_row(concept, seed_source):
    row = {
        "slug": concept["slug"],
        "title": concept["title"],
        "informal_statement": concept.get("informal_statement"),
        "wiedijk_number": concept.get("wiedijk_number"),
        "msc_primary": concept.get("msc_primary"),
        "seed_source": seed_source,
        "status": concept.get("status", "open"),
    }
    if "wikidata_id" in concept:  # absent → omit (merge-duplicates keeps prior)
        row["wikidata_id"] = concept["wikidata_id"]
    return row


def sync_file(path, supabase_url, service_key):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    seed_source = doc["seed_source"]
    synced = pending = 0
    for concept in doc["concepts"]:
        post(supabase_url, service_key,
             "atlas_concepts?on_conflict=slug",
             [_concept_row(concept, seed_source)],
             prefer="resolution=merge-duplicates,return=minimal")
        slug_q = urllib.parse.quote(concept["slug"], safe="")
        concept_rows = get_paged(supabase_url, service_key,
                                 f"atlas_concepts?slug=eq.{slug_q}&select=id")
        concept_id = concept_rows[0]["id"]
        for alignment in concept.get("alignments") or []:
            library = alignment["library"]
            name = alignment["native_name"]
            name_q = urllib.parse.quote(name, safe="")
            stmts = get_paged(
                supabase_url, service_key,
                f"atlas_statements?library_id=eq.{library}"
                f"&native_name=eq.{name_q}&select=id")
            if not stmts:
                print(f"ALIGNMENT PENDING: {library}/{name} not harvested yet")
                pending += 1
                continue
            post(supabase_url, service_key,
                 "atlas_alignments?on_conflict=concept_id,statement_id",
                 [{"concept_id": concept_id,
                   "statement_id": stmts[0]["id"],
                   "tier": alignment["tier"],
                   "evidence": alignment.get("evidence", {}),
                   "created_by": "seed:wiedijk100"}],
                 prefer="resolution=merge-duplicates,return=minimal")
            synced += 1
    return synced, pending


def main():
    # This script is PostgREST-only (the atlas-ingest edge function has no
    # concept/alignment actions). In ingest-only CI it must be a no-op, not
    # a job failure.
    if (os.environ.get("ATLAS_INGEST_URL") and os.environ.get("ATLAS_INGEST_TOKEN")
            and not (os.environ.get("ATLAS_SUPABASE_URL")
                     and os.environ.get("ATLAS_SUPABASE_SERVICE_KEY"))):
        print("sync_concepts requires direct PostgREST access "
              "(ATLAS_SUPABASE_SERVICE_KEY); skipping in ingest mode")
        return
    supabase_url, service_key = require_env()
    total_synced = total_pending = 0
    for path in sorted(CONCEPTS_DIR.glob("*.yaml")):
        synced, pending = sync_file(path, supabase_url, service_key)
        print(f"{path.name}: {synced} alignments synced, {pending} pending")
        total_synced += synced
        total_pending += pending
    print(f"total: {total_synced} alignments synced, {total_pending} pending")


if __name__ == "__main__":
    main()

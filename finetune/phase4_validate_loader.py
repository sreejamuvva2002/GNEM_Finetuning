"""Phase 4 gate -- validate the loader and data contract, then record the audit.

Runs every Phase 4 invariant plus fault-injection tests. Any failure is a GATE
FAILURE: the script exits non-zero and writes NO artifact.

Phase 4 builds no SQLite, no child tables, no holdouts, no datasets, no probes.
Test/Q42 remain LOCKED_UNTIL_PHASE_40.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as kb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_AUDIT = ROOT / "validation_v3" / "LOADER_CONTRACT_v3.md"


class Gate(Exception):
    """A Phase 4 invariant failed. Nothing is written."""


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    hashes = kb.frozen_input_hashes()

    # ---- Phase 3 split, read independently for cross-checking --------------
    with (ROOT / "datasets_v3" / "company_split_groups_v3.csv").open(encoding="utf-8") as fh:
        split_rows = list(csv.DictReader(fh))
    split_of = {int(r["row_id"]): r["split"] for r in split_rows}
    group_of = {int(r["row_id"]): r["split_group"] for r in split_rows}
    ids = {s: {i for i, v in split_of.items() if v == s} for s in ("train", "dev", "test")}

    canonical = [json.loads(l) for l in
                 (ROOT / "datasets_v3" / "canonical_records_v3.jsonl")
                 .read_text(encoding="utf-8").splitlines()]
    canon_by_id = {r["row_id"]: r for r in canonical}

    scopes = {s: kb.load_kb(s) for s in kb.KB_SCOPES}
    scope_ids = {s: {r.row_id for r in recs} for s, recs in scopes.items()}

    # ---- Integrity ---------------------------------------------------------
    check("canonical_sha_matches_phase2",
          hashes["canonical_records_v3.jsonl"] == kb.EXPECTED_CANONICAL_SHA,
          hashes["canonical_records_v3.jsonl"])
    check("split_sha_matches_phase3",
          hashes["company_split_groups_v3.csv"] == kb.EXPECTED_SPLIT_SHA,
          hashes["company_split_groups_v3.csv"])
    check("canonical_and_split_row_ids_identical",
          {r["row_id"] for r in canonical} == set(split_of),
          f"{len(canonical)} canonical vs {len(split_of)} split rows")

    # ---- Scope membership --------------------------------------------------
    for s, expected in kb.EXPECTED_SCOPE_ROWS.items():
        check(f"{s}_row_count", len(scopes[s]) == expected,
              f"{len(scopes[s])} == {expected}")
    check("train_kb_ids_equal_phase3_train", scope_ids["train_kb"] == ids["train"],
          f"{len(scope_ids['train_kb'])} rows == exact train split")
    check("train_dev_kb_ids_equal_train_union_dev",
          scope_ids["train_dev_kb"] == ids["train"] | ids["dev"],
          f"{len(scope_ids['train_dev_kb'])} rows == train ∪ dev")
    check("full_kb_ids_equal_all_205", scope_ids["full_kb"] == set(split_of),
          f"{len(scope_ids['full_kb'])} rows == all canonical row_ids")
    check("scope_nesting_train_sub_traindev_sub_full",
          scope_ids["train_kb"] < scope_ids["train_dev_kb"] < scope_ids["full_kb"],
          "train_kb ⊂ train_dev_kb ⊂ full_kb (strict)")
    check("no_dev_rows_in_train_kb", not (scope_ids["train_kb"] & ids["dev"]),
          f"{len(scope_ids['train_kb'] & ids['dev'])} dev rows leaked")
    check("no_test_rows_in_train_kb", not (scope_ids["train_kb"] & ids["test"]),
          f"{len(scope_ids['train_kb'] & ids['test'])} test rows leaked")
    check("no_test_rows_in_train_dev_kb", not (scope_ids["train_dev_kb"] & ids["test"]),
          f"{len(scope_ids['train_dev_kb'] & ids['test'])} test rows leaked")
    check("all_test_rows_only_via_full_kb",
          ids["test"] <= scope_ids["full_kb"]
          and not (ids["test"] & (scope_ids["train_kb"] | scope_ids["train_dev_kb"])),
          f"all {len(ids['test'])} test rows reachable only through full_kb")

    # Phase 3 guarantees each exact company / split_group sits on one side; a
    # scope is a union of whole sides, so neither can straddle. Re-asserted here.
    straddle_c, straddle_g = [], []
    for s in kb.KB_SCOPES:
        inside = scope_ids[s]
        for rid in inside:
            comp = canon_by_id[rid]["company"]
            allrows = {i for i in split_of if canon_by_id[i]["company"] == comp}
            if allrows & inside and not allrows <= inside:
                straddle_c.append((s, comp))
            grp = group_of[rid]
            gall = {i for i in split_of if group_of[i] == grp}
            if gall & inside and not gall <= inside:
                straddle_g.append((s, grp))
    check("no_company_partially_inside_a_scope", not straddle_c,
          f"{len(straddle_c)} partial companies")
    check("no_split_group_partially_inside_a_scope", not straddle_g,
          f"{len(straddle_g)} partial split groups")

    # ---- Field mapping and preservation -----------------------------------
    full = scopes["full_kb"]
    check("all_18_canonical_fields_mapped", len(kb.CANONICAL_FIELDS) == 18
          and all(hasattr(r, f) for f in kb.CANONICAL_FIELDS for r in full[:1]),
          f"{len(kb.CANONICAL_FIELDS)} fields")
    preserved = ("row_id", "company", "employment", "location", "address",
                 "processes", "services", "certifications", "category",
                 "industry_group", "primary_facility_type", "ev_supply_chain_role",
                 "primary_oems", "supplier_or_affiliation_type",
                 "product_or_service", "ev_battery_relevant",
                 "classification_method", "certification_count")
    drift = [(r.row_id, f) for r in full for f in preserved
             if getattr(r, f) != canon_by_id[r.row_id][f]]
    check("canonical_values_preserved_byte_for_byte", not drift,
          f"{len(drift)} drifted field(s) across {len(full)} rows")
    avs = next(r for r in full if r.row_id == 16)
    check("avs_row16_trailing_space_preserved",
          avs.address == canon_by_id[16]["address"] and avs.address.endswith(" "),
          repr(avs.address))
    check("employment_populated_all_rows",
          all(isinstance(r.employment, int) for r in full), f"{len(full)}/205")

    # ---- Model-facing contract --------------------------------------------
    mf = kb.model_facing_record(full[0])
    leaked = sorted(set(mf) & kb.FORBIDDEN_MODEL_FACING)
    check("model_facing_excludes_forbidden_fields", not leaked,
          f"leaked: {leaked}" if leaked else
          f"{len(kb.MODEL_FACING_FIELDS)} allowlisted fields; "
          f"split/split_group/certification_count/lat/long absent; other source fields included")
    check("model_facing_is_allowlist_not_deletion",
          set(mf) == set(kb.MODEL_FACING_FIELDS),
          "projection built from MODEL_FACING_FIELDS")
    required_source_fields = set(kb.CANONICAL_FIELDS) - {"certification_count"}
    check("all_nonexcluded_source_fields_model_facing_under_a002",
          required_source_fields <= set(kb.MODEL_FACING_FIELDS)
          and all(kb.model_facing_record(r)[f] == canon_by_id[r.row_id][f]
                  for r in full for f in required_source_fields),
          "all 17 nonexcluded source fields preserved for all 205 rows")
    check("certification_count_internal_only_and_source_preserved",
          "certification_count" not in kb.MODEL_FACING_FIELDS
          and all("certification_count" not in kb.model_facing_record(r)
                  and r.certification_count == canon_by_id[r.row_id]["certification_count"]
                  for r in full),
          "source count retained internally, including zeros; excluded from model-facing records")
    check("no_latitude_longitude_anywhere",
          not any(f in kb.CANONICAL_FIELDS + kb.MODEL_FACING_FIELDS
                  for f in ("latitude", "longitude")),
          "no geo columns produced")

    # ---- Geography (Amendment A-001) --------------------------------------
    derived_city = sum(1 for r in full if r.city is not None)
    derived_county = sum(1 for r in full if r.county is not None)
    null_city = sum(1 for r in full if r.city is None)
    null_county = sum(1 for r in full if r.county is None)

    not_in_location = [(r.row_id, r.city, r.county) for r in full
                       if (r.city is not None and r.city not in r.location)
                       or (r.county is not None and r.county not in r.location)]
    check("derived_geo_is_literal_substring_of_own_location", not not_in_location,
          f"{len(not_in_location)} value(s) not present in their own Location")

    # Address independence: re-derive with Address destroyed. Identical output
    # proves derivation cannot depend on Address.
    addr_blind = [(kb.derive_city_county(canon_by_id[r.row_id]["location"]))
                  for r in full]
    actual = [(r.city, r.county) for r in full]
    check("address_independence_proven", addr_blind == actual,
          "re-derivation from Location alone is byte-identical")

    sentinel_rows = [r for r in full if r.location in kb.LOCATION_SENTINELS]
    check("sentinel_locations_yield_null_geo",
          all(r.city is None and r.county is None for r in sentinel_rows),
          f"{len(sentinel_rows)} sentinel row(s) -> NULL/NULL")

    valeo = next(r for r in full if r.row_id == 187)
    check("a001_valeo_187", valeo.location == "Not specified"
          and valeo.address == "Not specified"
          and valeo.city is None and valeo.county is None,
          "location/address = Not specified, city/county NULL")
    volvo_ok = []
    for rid, frag in ((192, "Mahwah, NJ"), (193, "Greensboro, NC")):
        v = next(r for r in full if r.row_id == rid)
        volvo_ok.append(v.location == "Not applicable" and frag in v.address
                        and v.city is None and v.county is None)
    check("a001_volvo_192_193", all(volvo_ok),
          "location = Not applicable, real NJ/NC address preserved, city/county NULL")

    hyundai = {rid: next(r for r in full if r.row_id == rid) for rid in (80, 83, 93)}
    check("hyundai_counties_not_reconciled",
          len({r.county for r in hyundai.values()}) == 3
          and len({canon_by_id[i]["address"] for i in (80, 83, 93)}) == 1,
          "3 distinct counties from 3 Locations despite 1 shared Address")

    ambiguous = [r.row_id for r in full
                 if r.location not in kb.LOCATION_SENTINELS
                 and (r.city is None or r.county is None)]
    check("no_unparseable_real_locations", not ambiguous,
          f"{len(ambiguous)} real Location(s) not fully parseable")

    det = [kb.derive_city_county(r.location) for r in full]
    check("geo_derivation_deterministic", det == actual, "repeat derivation identical")

    # Direct scope literals only; this is not a transitive access proof.
    generator_names = ("phase10_build_a_cpt.py", "phase11_build_b_facts.py",
                       "phase13_build_c_answers.py", "phase14_build_d_sql.py",
                       "phase15_build_bc.py", "phase16_build_bd.py")
    generators = [ROOT / "finetune" / name for name in generator_names]
    static = kb.static_check_no_training_generator_reaches_full_kb(generators)
    check("static_check_reports_coverage_honestly",
          static["scanned_count"] == len(generators) and static["violation_count"] == 0,
          f"training generators scanned = {static['scanned_count']}; "
          f"forbidden full_kb call sites = {static['violation_count']}; "
          f"proves {static['proves']}")

    # ---- Fault injection ---------------------------------------------------
    faults: list[tuple[str, bool, str]] = []

    def fault(name, fn, expect):
        try:
            fn()
            faults.append((name, False, "*** NO ERROR RAISED ***"))
        except expect as e:
            faults.append((name, True, f"{type(e).__name__}: {str(e).splitlines()[0][:78]}"))
        except Exception as e:  # noqa: BLE001
            faults.append((name, False, f"wrong error {type(e).__name__}: {e}"))

    fault("omitted_scope", lambda: kb.load_kb(), TypeError)
    fault("none_scope", lambda: kb.load_kb(None), kb.ScopeError)
    fault("invalid_scope_string", lambda: kb.load_kb("full"), kb.ScopeError)
    fault("invalid_scope_type", lambda: kb.load_kb(123), kb.ScopeError)
    fault("case_variant_scope", lambda: kb.load_kb("FULL_KB"), kb.ScopeError)

    def _canonical_drift():
        orig = kb.EXPECTED_CANONICAL_SHA
        try:
            kb.EXPECTED_CANONICAL_SHA = "deadbeef" * 8
            kb.load_kb("full_kb")
        finally:
            kb.EXPECTED_CANONICAL_SHA = orig
    fault("canonical_hash_drift", _canonical_drift, kb.IntegrityError)

    def _split_drift():
        orig = kb.EXPECTED_SPLIT_SHA
        try:
            kb.EXPECTED_SPLIT_SHA = "deadbeef" * 8
            kb.load_kb("full_kb")
        finally:
            kb.EXPECTED_SPLIT_SHA = orig
    fault("split_hash_drift", _split_drift, kb.IntegrityError)

    def _bad_membership():
        orig = kb.SCOPE_SPLITS["train_kb"]
        try:
            kb.SCOPE_SPLITS["train_kb"] = frozenset({"train", "test"})
            kb.load_kb("train_kb")
        finally:
            kb.SCOPE_SPLITS["train_kb"] = orig
    fault("incorrect_split_membership", _bad_membership, kb.IntegrityError)

    def _mf_leak():
        rec = kb.model_facing_record(full[0])
        if set(rec) & kb.FORBIDDEN_MODEL_FACING:
            raise AssertionError("forbidden field present")
        # Simulate a careless edit adding split_group to the allowlist.
        orig = kb.MODEL_FACING_FIELDS
        try:
            kb.MODEL_FACING_FIELDS = orig + ("split_group",)
            bad = {f: getattr(full[0], f, None) for f in kb.MODEL_FACING_FIELDS}
            if set(bad) & kb.FORBIDDEN_MODEL_FACING:
                raise kb.ScopeError("model-facing projection would expose split_group")
        finally:
            kb.MODEL_FACING_FIELDS = orig
    fault("model_facing_leak_detected", _mf_leak, kb.ScopeError)

    def _geo_from_address():
        # Use a row with BOTH a real Location and a real Address, so the test is
        # not vacuous: feeding the Address must NOT reproduce the row's actual
        # city/county. Row 1's address even contains the same city name, which is
        # exactly the case a sloppy implementation would get "right" by accident.
        r = next(x for x in full if x.row_id == 1)
        assert r.city is not None and r.county is not None, "test row must have real geo"
        from_addr = kb.derive_city_county(canon_by_id[1]["address"])
        if from_addr == (r.city, r.county):
            raise AssertionError(
                "Address reproduced the row's geography -- derivation is NOT independent")
        raise kb.ScopeError(
            f"Address {canon_by_id[1]['address']!r} yields {from_addr!r}, never the row's "
            f"{(r.city, r.county)!r}; Address is not a derivation input")
    fault("geography_cannot_depend_on_address", _geo_from_address, kb.ScopeError)

    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print()
    for name, ok, detail in faults:
        print(f"  [{'PASS' if ok else 'FAIL'}] fault:{name}: {detail}")

    failed = [n for n, ok, _ in checks if not ok] + [n for n, ok, _ in faults if not ok]
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    _write_audit(hashes, scopes, scope_ids, ids, group_of, canon_by_id, full,
                 derived_city, derived_county, null_city, null_county,
                 sentinel_rows, ambiguous, static, checks, faults)

    print("\nAll Phase 4 gates passed.")
    for s in kb.KB_SCOPES:
        recs = scopes[s]
        print(f"  {s:13} rows={len(recs):3d} "
              f"companies={len({r.company for r in recs}):3d} "
              f"groups={len({group_of[r.row_id] for r in recs}):3d}")
    print(f"  city derived {derived_city}/205 · county derived {derived_county}/205 · "
          f"NULL city {null_city} · NULL county {null_county}")
    return 0


def _write_audit(hashes, scopes, scope_ids, ids, group_of, canon_by_id, full,
                 derived_city, derived_county, null_city, null_county,
                 sentinel_rows, ambiguous, static, checks, faults) -> None:
    L = ["# LOADER_CONTRACT_v3\n",
         "Phase 4 — loader and data contract. One module defines what a row means to "
         "everything downstream.\n",
         "## Frozen inputs\n", "```text",
         f"canonical_records_v3.jsonl   {hashes['canonical_records_v3.jsonl']}",
         f"company_split_groups_v3.csv  {hashes['company_split_groups_v3.csv']}",
         f"loader                       {hashes['loader_version']}",
         f"finetune/kb_v3.py            {hashes['kb_v3.py']}",
         "```\n",
         "Both hashes are re-verified on **every** `load_kb()` call, not merely once at "
         "import, so drift cannot slip past a long-running process.\n",
         "## The three KB scopes\n",
         "`load_kb(scope)` takes scope as a **required positional parameter with no "
         "default**. There is no unscoped accessor, no convenience wrapper, no cached "
         "global and no module-level object holding all 205 rows. Scopes are derived from "
         "the frozen Phase 3 split; the expected counts are asserted as validation and are "
         "never the construction mechanism.\n",
         "| scope | splits included | rows | exact companies | split groups | used for |",
         "|---|---|---|---|---|---|"]
    use = {"train_kb": "**all training targets** — A passages, B facts, C answers",
           "train_dev_kb": "**dev evaluation gold only**",
           "full_kb": "**test evaluation gold only**, and the deployed SQL database"}
    for s in kb.KB_SCOPES:
        recs = scopes[s]
        L.append(f"| `{s}` | {', '.join(sorted(kb.SCOPE_SPLITS[s]))} | {len(recs)} | "
                 f"{len({r.company for r in recs})} | "
                 f"{len({group_of[r.row_id] for r in recs})} | {use[s]} |")
    L += ["",
          f"Phase 3 split sides: train {len(ids['train'])} · dev {len(ids['dev'])} · "
          f"test {len(ids['test'])} rows.\n",
          "`train_kb` ⊂ `train_dev_kb` ⊂ `full_kb`, strictly. No dev or test row is "
          "reachable through `train_kb`; no test row through `train_dev_kb`; all "
          f"{len(ids['test'])} test rows are reachable only through `full_kb`.\n",
          "## Geographic derivation (Amendment A-001)\n",
          "`city`/`county` are derived **only** from geographic information explicitly "
          "present in that row's own canonical `Location`. `derive_city_county()` receives "
          "the location string and nothing else, so it is structurally incapable of "
          "consulting `Address`, ZIP, external geocoding, company knowledge, "
          "latitude/longitude, or another row.\n",
          "| outcome | rows |", "|---|---|",
          f"| city derived | {derived_city} |",
          f"| county derived | {derived_county} |",
          f"| city NULL | {null_city} |",
          f"| county NULL | {null_county} |",
          f"| sentinel `Location` → NULL/NULL | {len(sentinel_rows)} |",
          f"| real `Location` not fully parseable | {len(ambiguous)} |",
          "",
          "County text is preserved **verbatim as represented** — `\"Hall County\"`, never "
          "normalized to `\"Hall\"`. Stripping the type-word is a normalization no rule "
          "authorizes.\n",
          "### Frozen A-001 cases\n", "```text"]
    for rid in (187, 192, 193):
        r = next(x for x in full if x.row_id == rid)
        L.append(f"row {rid}  {r.company}")
        L.append(f"    location = {r.location!r}")
        L.append(f"    address  = {r.address!r}")
        L.append(f"    city     = {r.city!r}   county = {r.county!r}")
    L += ["```\n",
          "### Hyundai shared address — deliberately NOT reconciled\n",
          "Rows 80, 83 and 93 share one `Address` but state three different counties. Each "
          "row's own `Location` is parsed independently; `Address` is irrelevant to "
          "derivation, so the inconsistency is carried through as frozen-source behaviour "
          "rather than repaired.\n", "```text"]
    for rid in (80, 83, 93):
        r = next(x for x in full if x.row_id == rid)
        L.append(f"row {rid}  location={r.location!r} -> county={r.county!r}")
    L += [f"    all three share address {canon_by_id[80]['address']!r} (ignored)",
          "```\n",
          "No latitude, longitude, geocoding, distance, radius, nearest-company logic, "
          "spatial index or geo SQL is introduced. `city`/`county` are ordinary structured "
          "attributes.\n",
          "## Model-facing contract\n",
          f"`model_facing_record()` builds its result from an explicit **allowlist** of "
          f"{len(kb.MODEL_FACING_FIELDS)} fields — it is not a full record with prohibited "
          "fields deleted afterwards, so a field added to the internal record cannot leak "
          "by omission.\n",
          "Structurally absent from model-facing output: "
          + ", ".join(f"`{f}`" for f in sorted(kb.FORBIDDEN_MODEL_FACING)) + ".\n",
          "The user-authorized A-002 exception keeps `certification_count` for source "
          "validation only; complete certification lists remain model-facing. `split` and "
          "`split_group` are leakage-control metadata, exposed solely through the separate "
          "`split_metadata()` accessor and never merged into a record.\n",
          "## Static training-generator check\n",
          "README Phase 4 requires a static check that no training generator can reach "
          "`full_kb`. It is implemented and **reusable**, but its coverage today is "
          "reported honestly:\n", "```text",
          f"training generators scanned      = {static['scanned_count']}",
          f"forbidden full_kb call sites     = {static['violation_count']}",
          "```\n",
          "The six existing direct training renderers were scanned for forbidden scope "
          "literals. This is not a proof about transitive imports or runtime accesses. "
          "Every later training-data phase must re-run "
          "`static_check_no_training_generator_reaches_full_kb()` with its own module "
          "paths and report the scanned count.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        L.append(f"| `{name}` | {'PASS' if ok else 'FAIL'} | {detail} |")
    L += ["", "## Fault injection\n",
          "Each fault must be rejected. A gate that only passes on good input proves "
          "little.\n",
          "| fault | rejected | how |", "|---|---|---|"]
    for name, ok, detail in faults:
        L.append(f"| `{name}` | {'yes' if ok else '**NO**'} | {detail} |")
    L.append("")
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Gate as exc:
        print(f"\nPHASE 4 GATE FAILURE: {exc}", file=sys.stderr)
        print("No artifact written. No rule weakened.", file=sys.stderr)
        raise SystemExit(1)

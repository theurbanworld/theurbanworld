# Future Work: Data Quality Fixes

Use this document as a prompt for a new Claude Code session.

---

## Context

The city data pipeline has data quality issues identified by the validation script (`src/s99_validate_cities.py`). Run `uv run python -m src.s99_validate_cities` to see current status.

## Task 1: Use UCDB as Canonical City List

**Problem**: The pipeline uses MTUC data for population calculations (s04a, s04b) but filters to UCDB cities in s02c. This creates 2,648 orphaned city_ids in downstream tables.

**Goal**: All downstream datasets should only include cities from `cities.parquet` (UCDB-based).

**Files to modify**:
- `src/s04a_compute_city_populations.py` - Filter H3 data to only UCDB city_ids
- `src/s04b_compute_city_rankings.py` - Filter rankings to only UCDB city_ids

**Approach**:
1. Read the canonical city list from `data/processed/cities/cities.parquet`
2. At the start of processing, filter input data to only include these city_ids
3. Run validation to confirm orphan warnings are resolved

**Expected outcome**: `populations`, `rankings`, `growth`, `peers` should all have 0 orphaned city_ids.

---

## Task 2: Deduplicate Border Cities

**Problem**: 11 city_ids appear twice in `cities.parquet` because border cities (Aachen, Jerusalem, Maastricht, etc.) exist in multiple countries in the source data.

**Goal**: Keep one record per city_id.

**Files to modify**:
- `src/s02c_generate_cities.py`

**Approach**:
1. After loading/joining data, group by `city_id`
2. For duplicates, keep the record with:
   - Largest population (primary tiebreaker)
   - Or first alphabetically by country_code (secondary)
3. Log which duplicates were removed and why

**Expected outcome**: `cities.parquet` should have exactly 11,422 rows (currently 11,433).

---

## Task 3: Fill Missing Peer Names

**Problem**: 19.3% (11,707 records) in `city_density_peers.parquet` have NULL `peer_name`.

**Goal**: Join peer names from `cities.parquet`.

**Files to modify**:
- `src/s04b_compute_city_rankings.py` (in the density peers section)

**Approach**:
1. After computing density peers, join with cities to get names
2. Use `cities.name` for `peer_name` where currently NULL

**Expected outcome**: 0% NULL peer_names (except for orphaned peer_city_ids which will be fixed by Task 1).

---

## Task 4: Add JSON Report Output

**Problem**: Validation output is console-only, not suitable for CI/CD.

**Goal**: Add `--json` flag to output validation results as JSON.

**Files to modify**:
- `src/s99_validate_cities.py`

**Approach**:
1. Add `--json` / `--output` CLI options
2. Collect all results into a dict structure
3. Write to file or stdout as JSON
4. Include timestamp, file paths, error/warning counts, details

**Expected outcome**: `uv run python -m src.s99_validate_cities --json > report.json`

---

## Validation

After each task, run:
```bash
uv run python -m src.s99_validate_cities
```

Expected final output:
```
cities.parquet (11,422 rows): [PASS]
populations.parquet: [PASS]
rankings.parquet: [PASS]
growth.parquet: [PASS]
peers.parquet: [PASS]

--- Data Quality Checks ---
  All checks passed!

Summary
Errors: 0
Warnings: 0
```

---

## Reference Files

- Validation script: `src/s99_validate_cities.py`
- City generation: `src/s02c_generate_cities.py`
- Population computation: `src/s04a_compute_city_populations.py`
- Rankings/growth/peers: `src/s04b_compute_city_rankings.py`
- Output data: `data/processed/cities/*.parquet`

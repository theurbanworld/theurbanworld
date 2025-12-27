"""
Validate city data quality using Pandera.

Purpose: Run data quality checks on all city parquet files, identifying schema
         violations, referential integrity issues, and data anomalies.

Input:
  - data/processed/cities/cities.parquet
  - data/processed/cities/city_populations.parquet
  - data/processed/cities/city_rankings.parquet
  - data/processed/cities/city_growth.parquet
  - data/processed/cities/city_density_peers.parquet

Output:
  - Console validation report with PASS/FAIL/WARN status
  - Exit code 0 (all pass) or 1 (errors found)

Decision log:
  - Uses Pandera with Ibis backend for lazy evaluation on parquet files
  - Referential integrity checked separately (not built into Pandera)
  - Warn-only mode: does not block pipeline on failures
  - Known issues documented in schema definitions
Date: 2025-12-27
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import click
import ibis
import pandera.ibis as pa
from pandera.ibis import DataFrameModel, Field

from .utils.config import get_processed_path


# =============================================================================
# Schema Definitions
# =============================================================================


class CitySchema(DataFrameModel):
    """Schema for cities.parquet - primary city metadata."""

    city_id: str = Field(nullable=False)
    name: str = Field(nullable=True)  # 14 known NULLs
    country_name: str = Field(nullable=True)
    country_code: str = Field(nullable=True)
    region: str = Field(nullable=True)
    ucdb_year_of_birth: int = Field(ge=1975, le=2025, nullable=True)
    ucdb_population_2025: int = Field(ge=0, nullable=True)
    ucdb_area_km2_2025: float = Field(gt=0, nullable=True)

    class Config:
        strict = False  # Allow extra columns (geometry, bbox, etc.)
        coerce = True


class CityPopulationSchema(DataFrameModel):
    """Schema for city_populations.parquet - population time series."""

    city_id: str = Field(nullable=False)
    epoch: int = Field(ge=1975, le=2030, nullable=False)
    population: float = Field(ge=0, nullable=False)
    area_km2: float = Field(gt=0, nullable=False)
    density_per_km2: float = Field(ge=0, nullable=False)
    cell_count: int = Field(ge=1, nullable=False)

    class Config:
        strict = False
        coerce = True


class CityGrowthSchema(DataFrameModel):
    """Schema for city_growth.parquet - 1975-2030 growth metrics."""

    city_id: str = Field(nullable=False)
    cagr_1975_2030: float = Field(nullable=True)  # 61% NULL (expected)
    growth_regime: str = Field(nullable=True)
    relative_acceleration: float = Field(nullable=True)
    world_baseline_cagr: float = Field(nullable=True)

    class Config:
        strict = False
        coerce = True


class CityRankingSchema(DataFrameModel):
    """Schema for city_rankings.parquet - per-epoch rankings."""

    city_id: str = Field(nullable=False)
    name: str = Field(nullable=True)  # 8.2% NULL
    epoch: int = Field(ge=1975, le=2030, nullable=False)
    population: float = Field(ge=0, nullable=False)
    global_population_rank: int = Field(ge=1, nullable=False)
    global_density_rank: int = Field(ge=1, nullable=False)

    class Config:
        strict = False
        coerce = True


class CityDensityPeersSchema(DataFrameModel):
    """Schema for city_density_peers.parquet - peer relationships."""

    city_id: str = Field(nullable=False)
    peer_city_id: str = Field(nullable=False)
    peer_name: str = Field(nullable=True)  # 19% NULL
    peer_population: int = Field(ge=0, nullable=False)
    peer_density: float = Field(gt=0, nullable=False)
    density_ratio: float = Field(gt=0, nullable=False)

    class Config:
        strict = False
        coerce = True


# =============================================================================
# Type Casting Helpers
# =============================================================================


def cast_int_columns_to_int64(table):
    """
    Cast all integer columns to int64 for Pandera compatibility.

    Parquet files often use int32/uint32 for efficiency, but Pandera's Ibis
    backend expects int64. This function normalizes integer types.
    """
    # Types that need to be cast to int64
    types_to_cast = {"int8", "int16", "int32", "uint8", "uint16", "uint32"}

    mutations = {}
    for col_name in table.columns:
        col_type = str(table[col_name].type())
        if col_type in types_to_cast:
            mutations[col_name] = table[col_name].cast("int64")
    if mutations:
        return table.mutate(**mutations)
    return table


# =============================================================================
# Validation Result Tracking
# =============================================================================


@dataclass
class ValidationResult:
    """Result of validating a single table."""

    table_name: str
    row_count: int
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_table(table, schema, table_name: str) -> ValidationResult:
    """Validate a single table against its schema."""
    errors = []
    warnings = []
    passed = True

    # Get row count
    row_count = table.count().execute()

    # Cast integer columns to int64 for Pandera compatibility
    table = cast_int_columns_to_int64(table)

    try:
        schema.validate(table, lazy=True)
    except pa.errors.SchemaErrors as e:
        passed = False
        # Parse the schema errors from the exception
        for err in e.schema_errors:
            if isinstance(err, dict):
                col = err.get("column", "unknown")
                check = err.get("check", str(err))
                errors.append(f"{col}: {check}")
            else:
                # SchemaError object
                errors.append(str(err))
    except Exception as e:
        passed = False
        errors.append(f"Validation error: {e}")

    return ValidationResult(
        table_name=table_name,
        row_count=row_count,
        passed=passed,
        errors=errors,
        warnings=warnings,
    )


# =============================================================================
# Cross-Table Validation (Foreign Keys & Duplicates)
# =============================================================================


def check_duplicate_keys(tables: dict) -> list[str]:
    """Check for duplicate primary keys in cities table."""
    warnings = []

    # Check cities.parquet for duplicate city_ids using Ibis
    cities = tables["cities"]

    # Use Ibis to find duplicates (more efficient than pandas)
    dup_query = (
        cities.group_by("city_id")
        .agg(count=cities.city_id.count())
        .filter(lambda t: t["count"] > 1)
    )
    duplicates = dup_query.execute()

    if len(duplicates) > 0:
        examples = duplicates["city_id"].head(5).tolist()
        warnings.append(
            f"cities: {len(duplicates)} duplicate city_ids found (e.g., {examples})"
        )

    return warnings


def check_foreign_keys(tables: dict) -> list[str]:
    """Check referential integrity between tables."""
    warnings = []
    cities = tables["cities"]
    valid_ids = set(cities.select("city_id").distinct().execute()["city_id"].tolist())

    child_tables = ["populations", "rankings", "growth", "peers"]
    for name in child_tables:
        if name not in tables:
            continue
        table = tables[name]
        if "city_id" not in table.columns:
            continue

        table_ids = set(table.select("city_id").distinct().execute()["city_id"].tolist())
        orphaned = table_ids - valid_ids

        if orphaned:
            examples = list(orphaned)[:3]
            warnings.append(
                f"{name}: {len(orphaned)} city_ids not in cities.parquet "
                f"(e.g., {examples})"
            )

    # Check peer_city_id in density_peers
    if "peers" in tables:
        peer_ids = set(
            tables["peers"]
            .select("peer_city_id")
            .distinct()
            .execute()["peer_city_id"]
            .tolist()
        )
        orphaned_peers = peer_ids - valid_ids
        if orphaned_peers:
            warnings.append(
                f"peers: {len(orphaned_peers)} peer_city_ids not in cities.parquet"
            )

    return warnings


def check_growth_regimes(tables: dict) -> list[str]:
    """Check that growth_regime values are valid."""
    warnings = []
    valid_regimes = {"explosive", "growing", "stable", "shrinking"}

    if "growth" not in tables:
        return warnings

    growth = tables["growth"]
    regimes = growth.select("growth_regime").distinct().execute()["growth_regime"].tolist()
    invalid = [r for r in regimes if r is not None and r not in valid_regimes]

    if invalid:
        warnings.append(f"growth: invalid growth_regime values: {invalid}")

    return warnings


def check_epoch_coverage(tables: dict) -> list[str]:
    """Check that all expected epochs are present."""
    warnings = []
    expected_epochs = set(range(1975, 2031, 5))  # 1975, 1980, ..., 2030

    for name in ["populations", "rankings"]:
        if name not in tables:
            continue
        table = tables[name]
        epochs = set(table.select("epoch").distinct().execute()["epoch"].tolist())
        missing = expected_epochs - epochs

        if missing:
            warnings.append(f"{name}: missing epochs {sorted(missing)}")

    return warnings


def check_row_count_match(tables: dict) -> list[str]:
    """Check that city_populations and city_rankings have the same row count."""
    warnings = []

    if "populations" not in tables or "rankings" not in tables:
        return warnings

    pop_count = tables["populations"].count().execute()
    rank_count = tables["rankings"].count().execute()

    if pop_count != rank_count:
        warnings.append(
            f"Row count mismatch: city_populations ({pop_count:,}) "
            f"vs city_rankings ({rank_count:,})"
        )

    return warnings


# =============================================================================
# Main
# =============================================================================


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def main(verbose: bool = False):
    """Validate city data quality."""
    print("=" * 60)
    print("City Data Validation Report")
    print("=" * 60)

    # Connect and load tables
    data_dir = get_processed_path("cities")
    con = ibis.duckdb.connect()

    files = {
        "cities": "cities.parquet",
        "populations": "city_populations.parquet",
        "rankings": "city_rankings.parquet",
        "growth": "city_growth.parquet",
        "peers": "city_density_peers.parquet",
    }

    tables = {}
    for name, filename in files.items():
        path = data_dir / filename
        if path.exists():
            tables[name] = con.read_parquet(str(path))
        else:
            print(f"  SKIP: {filename} (not found)")

    schemas = {
        "cities": CitySchema,
        "populations": CityPopulationSchema,
        "rankings": CityRankingSchema,
        "growth": CityGrowthSchema,
        "peers": CityDensityPeersSchema,
    }

    # Validate each table against its schema
    print("\n--- Schema Validation ---")
    results = []
    for name, table in tables.items():
        if name not in schemas:
            continue
        result = validate_table(table, schemas[name], name)
        results.append(result)

        status = "PASS" if result.passed else "FAIL"
        print(f"{name}.parquet ({result.row_count:,} rows): [{status}]")
        for err in result.errors:
            print(f"  ERROR: {err}")
        for warn in result.warnings:
            print(f"  WARN: {warn}")

    # Cross-table validation
    print("\n--- Data Quality Checks ---")

    # Check for duplicate keys
    dup_warnings = check_duplicate_keys(tables)
    for warn in dup_warnings:
        print(f"  WARN: {warn}")

    # Check foreign keys
    fk_warnings = check_foreign_keys(tables)
    for warn in fk_warnings:
        print(f"  WARN: {warn}")

    # Check growth regimes
    regime_warnings = check_growth_regimes(tables)
    for warn in regime_warnings:
        print(f"  WARN: {warn}")

    # Check epoch coverage
    epoch_warnings = check_epoch_coverage(tables)
    for warn in epoch_warnings:
        print(f"  WARN: {warn}")

    # Check row count match
    count_warnings = check_row_count_match(tables)
    for warn in count_warnings:
        print(f"  WARN: {warn}")

    if not (dup_warnings or fk_warnings or regime_warnings or epoch_warnings or count_warnings):
        print("  All checks passed!")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = (
        len(dup_warnings)
        + len(fk_warnings)
        + len(regime_warnings)
        + len(epoch_warnings)
        + len(count_warnings)
        + sum(len(r.warnings) for r in results)
    )
    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    # Note about known issues
    if verbose and total_warnings > 0:
        print("\nNote: Some warnings are expected:")
        print("  - Orphaned city_ids: pipeline uses MTUC for populations but")
        print("    filters to UCDB for cities.parquet (future fix needed)")
        print("  - Duplicate city_ids: border cities appear in multiple countries")
        print("    (will be deduplicated in future fix)")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

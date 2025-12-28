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

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
# Statistical Outlier Detection
# =============================================================================


def check_population_spikes(tables: dict, threshold: float = 1.0) -> list[dict]:
    """
    Flag cities with >100% population growth between adjacent epochs.

    Args:
        tables: Dict of Ibis tables
        threshold: Growth rate threshold (1.0 = 100%)

    Returns:
        List of outlier records with city_id, epoch, growth_rate, population
    """
    if "populations" not in tables:
        return []

    pop = tables["populations"]
    df = pop.select(["city_id", "epoch", "population"]).execute()

    # Sort and compute growth rates
    df = df.sort_values(["city_id", "epoch"])
    df["prev_pop"] = df.groupby("city_id")["population"].shift(1)
    df["growth_rate"] = (df["population"] - df["prev_pop"]) / df["prev_pop"]

    # Filter to spikes
    spikes = df[df["growth_rate"] > threshold].copy()

    return [
        {
            "city_id": row["city_id"],
            "epoch": int(row["epoch"]),
            "growth_rate": round(row["growth_rate"] * 100, 1),
            "population": int(row["population"]),
        }
        for _, row in spikes.iterrows()
    ]


def check_population_decline(tables: dict, threshold: float = 0.5) -> list[dict]:
    """
    Flag cities losing >50% population between epochs.

    Args:
        tables: Dict of Ibis tables
        threshold: Decline rate threshold (0.5 = 50%)

    Returns:
        List of outlier records with city_id, epoch, decline_rate, population
    """
    if "populations" not in tables:
        return []

    pop = tables["populations"]
    df = pop.select(["city_id", "epoch", "population"]).execute()

    # Sort and compute decline rates
    df = df.sort_values(["city_id", "epoch"])
    df["prev_pop"] = df.groupby("city_id")["population"].shift(1)
    df["decline_rate"] = (df["prev_pop"] - df["population"]) / df["prev_pop"]

    # Filter to declines
    declines = df[df["decline_rate"] > threshold].copy()

    return [
        {
            "city_id": row["city_id"],
            "epoch": int(row["epoch"]),
            "decline_rate": round(row["decline_rate"] * 100, 1),
            "population": int(row["population"]),
        }
        for _, row in declines.iterrows()
    ]


def check_extreme_densities(tables: dict, threshold: float = 50000) -> list[dict]:
    """
    Flag cities with density >50,000/km² (potential data artifacts).

    Known real-world maximums: Dhaka ~45,000, Manila ~43,000/km².

    Args:
        tables: Dict of Ibis tables
        threshold: Density threshold in people/km²

    Returns:
        List of outlier records with city_id, epoch, density, name
    """
    if "rankings" not in tables:
        return []

    rankings = tables["rankings"]
    df = rankings.select(
        ["city_id", "name", "epoch", "density_per_km2"]
    ).execute()

    # Filter to extreme densities
    extreme = df[df["density_per_km2"] > threshold].copy()

    return [
        {
            "city_id": row["city_id"],
            "name": row["name"],
            "epoch": int(row["epoch"]),
            "density": round(row["density_per_km2"], 0),
        }
        for _, row in extreme.iterrows()
    ]


def check_regional_density_outliers(tables: dict, z_threshold: float = 3.0) -> list[dict]:
    """
    Flag cities >3σ from their region's mean density at 2025.

    Args:
        tables: Dict of Ibis tables
        z_threshold: Number of standard deviations for outlier detection

    Returns:
        List of outlier records with city_id, name, region, density, z_score
    """
    if "rankings" not in tables or "cities" not in tables:
        return []

    # Get 2025 rankings with region info
    rankings = tables["rankings"]
    cities = tables["cities"]

    rankings_2025 = rankings.filter(rankings["epoch"] == 2025).select(
        ["city_id", "name", "density_per_km2"]
    )
    city_regions = cities.select(["city_id", "region"])

    # Join to get region
    joined = rankings_2025.join(city_regions, "city_id").execute()

    # Compute z-scores per region
    region_stats = joined.groupby("region").agg(
        mean_density=("density_per_km2", "mean"),
        std_density=("density_per_km2", "std"),
    )
    joined = joined.merge(region_stats, on="region")
    joined["z_score"] = (
        (joined["density_per_km2"] - joined["mean_density"]) / joined["std_density"]
    )

    # Filter to outliers
    outliers = joined[joined["z_score"].abs() > z_threshold].copy()

    return [
        {
            "city_id": row["city_id"],
            "name": row["name"],
            "region": row["region"],
            "density": round(row["density_per_km2"], 0),
            "z_score": round(row["z_score"], 2),
        }
        for _, row in outliers.iterrows()
    ]


def check_rank_volatility(tables: dict, threshold: int = 5000) -> list[dict]:
    """
    Flag cities with >5,000 rank change between epochs.

    Args:
        tables: Dict of Ibis tables
        threshold: Minimum rank change to flag

    Returns:
        List of outlier records with city_id, name, epoch, rank_change
    """
    if "rankings" not in tables:
        return []

    rankings = tables["rankings"]
    df = rankings.select(
        ["city_id", "name", "epoch", "global_population_rank"]
    ).execute()

    # Sort and compute rank changes
    df = df.sort_values(["city_id", "epoch"])
    df["prev_rank"] = df.groupby("city_id")["global_population_rank"].shift(1)
    df["rank_change"] = df["global_population_rank"] - df["prev_rank"]

    # Filter to volatile rankings (large positive or negative changes)
    volatile = df[df["rank_change"].abs() > threshold].copy()

    return [
        {
            "city_id": row["city_id"],
            "name": row["name"],
            "epoch": int(row["epoch"]),
            "rank_change": int(row["rank_change"]),
            "new_rank": int(row["global_population_rank"]),
        }
        for _, row in volatile.iterrows()
    ]


def check_temporal_gaps(tables: dict) -> list[dict]:
    """
    Flag cities that disappear then reappear across epochs.

    Example: City exists in 1990, missing in 1995, back in 2000.

    Returns:
        List of records with city_id, missing_epochs, present_epochs
    """
    if "populations" not in tables:
        return []

    pop = tables["populations"]
    df = pop.select(["city_id", "epoch"]).execute()

    expected_epochs = set(range(1975, 2031, 5))

    # Group by city_id and find epochs
    city_epochs = df.groupby("city_id")["epoch"].apply(set).reset_index()
    city_epochs.columns = ["city_id", "epochs"]

    gaps = []
    for _, row in city_epochs.iterrows():
        epochs = sorted(row["epochs"])
        if len(epochs) < 2:
            continue

        # Check for gaps between first and last epoch
        first, last = min(epochs), max(epochs)
        expected_in_range = {e for e in expected_epochs if first <= e <= last}
        missing = expected_in_range - row["epochs"]

        if missing:
            gaps.append({
                "city_id": row["city_id"],
                "missing_epochs": sorted(missing),
                "present_epochs": epochs,
            })

    return gaps


def check_growth_regime_consistency(tables: dict) -> list[dict]:
    """
    Verify growth_regime classification matches CAGR thresholds.

    Expected thresholds:
      - explosive: CAGR >= 0.03 (3%)
      - growing: 0.01 <= CAGR < 0.03
      - stable: 0 <= CAGR < 0.01
      - shrinking: CAGR < 0

    Returns:
        List of misclassified records with city_id, cagr, regime, expected_regime
    """
    if "growth" not in tables:
        return []

    growth = tables["growth"]
    df = growth.select(["city_id", "cagr_1975_2030", "growth_regime"]).execute()

    # Filter out NULL CAGRs
    df = df[df["cagr_1975_2030"].notna()].copy()

    def expected_regime(cagr):
        if cagr >= 0.03:
            return "explosive"
        elif cagr >= 0.01:
            return "growing"
        elif cagr >= 0:
            return "stable"
        else:
            return "shrinking"

    df["expected_regime"] = df["cagr_1975_2030"].apply(expected_regime)

    # Find mismatches
    mismatches = df[df["growth_regime"] != df["expected_regime"]].copy()

    return [
        {
            "city_id": row["city_id"],
            "cagr": round(row["cagr_1975_2030"] * 100, 2),
            "regime": row["growth_regime"],
            "expected_regime": row["expected_regime"],
        }
        for _, row in mismatches.iterrows()
    ]


# =============================================================================
# Main
# =============================================================================


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.option("--output", "-o", type=click.Path(), help="Write JSON to file (implies --json)")
@click.option("--check-outliers/--no-check-outliers", default=True, help="Run statistical outlier detection")
def main(verbose: bool = False, output_json: bool = False, output: str | None = None, check_outliers: bool = True):
    """Validate city data quality."""
    # If --output is specified, enable JSON mode
    if output:
        output_json = True

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
    missing_files = []
    for name, filename in files.items():
        path = data_dir / filename
        if path.exists():
            tables[name] = con.read_parquet(str(path))
        else:
            missing_files.append(filename)
            if not output_json:
                print(f"  SKIP: {filename} (not found)")

    schemas = {
        "cities": CitySchema,
        "populations": CityPopulationSchema,
        "rankings": CityRankingSchema,
        "growth": CityGrowthSchema,
        "peers": CityDensityPeersSchema,
    }

    # Validate each table against its schema
    if not output_json:
        print("=" * 60)
        print("City Data Validation Report")
        print("=" * 60)
        print("\n--- Schema Validation ---")

    results = []
    for name, table in tables.items():
        if name not in schemas:
            continue
        result = validate_table(table, schemas[name], name)
        results.append(result)

        if not output_json:
            status = "PASS" if result.passed else "FAIL"
            print(f"{name}.parquet ({result.row_count:,} rows): [{status}]")
            for err in result.errors:
                print(f"  ERROR: {err}")
            for warn in result.warnings:
                print(f"  WARN: {warn}")

    # Cross-table validation
    if not output_json:
        print("\n--- Data Quality Checks ---")

    # Collect all data quality warnings
    all_quality_warnings = {}

    dup_warnings = check_duplicate_keys(tables)
    if dup_warnings:
        all_quality_warnings["duplicate_keys"] = dup_warnings
    for warn in dup_warnings:
        if not output_json:
            print(f"  WARN: {warn}")

    fk_warnings = check_foreign_keys(tables)
    if fk_warnings:
        all_quality_warnings["foreign_keys"] = fk_warnings
    for warn in fk_warnings:
        if not output_json:
            print(f"  WARN: {warn}")

    regime_warnings = check_growth_regimes(tables)
    if regime_warnings:
        all_quality_warnings["growth_regimes"] = regime_warnings
    for warn in regime_warnings:
        if not output_json:
            print(f"  WARN: {warn}")

    epoch_warnings = check_epoch_coverage(tables)
    if epoch_warnings:
        all_quality_warnings["epoch_coverage"] = epoch_warnings
    for warn in epoch_warnings:
        if not output_json:
            print(f"  WARN: {warn}")

    count_warnings = check_row_count_match(tables)
    if count_warnings:
        all_quality_warnings["row_count_match"] = count_warnings
    for warn in count_warnings:
        if not output_json:
            print(f"  WARN: {warn}")

    if not output_json:
        if not all_quality_warnings:
            print("  All checks passed!")

    # Statistical outlier detection
    statistical_checks = {}
    if check_outliers:
        if not output_json:
            print("\n--- Statistical Outlier Detection ---")

        # Population spikes
        pop_spikes = check_population_spikes(tables)
        if pop_spikes:
            statistical_checks["population_spikes"] = pop_spikes
            if not output_json:
                print(f"  INFO: {len(pop_spikes)} cities with >100% population growth between epochs")
                if verbose:
                    for item in pop_spikes[:5]:
                        print(f"    - {item['city_id']}: +{item['growth_rate']}% at {item['epoch']}")

        # Population declines
        pop_declines = check_population_decline(tables)
        if pop_declines:
            statistical_checks["population_declines"] = pop_declines
            if not output_json:
                print(f"  INFO: {len(pop_declines)} cities with >50% population decline between epochs")
                if verbose:
                    for item in pop_declines[:5]:
                        print(f"    - {item['city_id']}: -{item['decline_rate']}% at {item['epoch']}")

        # Extreme densities
        extreme_densities = check_extreme_densities(tables)
        if extreme_densities:
            statistical_checks["extreme_densities"] = extreme_densities
            if not output_json:
                print(f"  INFO: {len(extreme_densities)} city-epochs with density >50,000/km²")
                if verbose:
                    for item in extreme_densities[:5]:
                        print(f"    - {item['name']} ({item['city_id']}): {item['density']:,.0f}/km² at {item['epoch']}")

        # Regional density outliers
        regional_outliers = check_regional_density_outliers(tables)
        if regional_outliers:
            statistical_checks["regional_density_outliers"] = regional_outliers
            if not output_json:
                print(f"  INFO: {len(regional_outliers)} cities >3σ from regional mean density")
                if verbose:
                    for item in regional_outliers[:5]:
                        print(f"    - {item['name']}: z={item['z_score']} in {item['region']}")

        # Rank volatility
        rank_volatile = check_rank_volatility(tables)
        if rank_volatile:
            statistical_checks["rank_volatility"] = rank_volatile
            if not output_json:
                print(f"  INFO: {len(rank_volatile)} cities with >5,000 rank change between epochs")
                if verbose:
                    for item in rank_volatile[:5]:
                        print(f"    - {item['name']}: {item['rank_change']:+d} at {item['epoch']}")

        # Temporal gaps
        temporal_gaps = check_temporal_gaps(tables)
        if temporal_gaps:
            statistical_checks["temporal_gaps"] = temporal_gaps
            if not output_json:
                print(f"  INFO: {len(temporal_gaps)} cities with gaps in epoch coverage")
                if verbose:
                    for item in temporal_gaps[:5]:
                        print(f"    - {item['city_id']}: missing {item['missing_epochs']}")

        # Growth regime consistency
        regime_mismatches = check_growth_regime_consistency(tables)
        if regime_mismatches:
            statistical_checks["regime_mismatches"] = regime_mismatches
            if not output_json:
                print(f"  INFO: {len(regime_mismatches)} cities with misclassified growth regime")
                if verbose:
                    for item in regime_mismatches[:5]:
                        print(f"    - {item['city_id']}: {item['regime']} but CAGR={item['cagr']}% (expected {item['expected_regime']})")

        if not output_json and not statistical_checks:
            print("  No outliers detected")

    # Calculate totals
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = (
        len(dup_warnings)
        + len(fk_warnings)
        + len(regime_warnings)
        + len(epoch_warnings)
        + len(count_warnings)
        + sum(len(r.warnings) for r in results)
    )
    total_outliers = sum(len(v) for v in statistical_checks.values())

    # Build JSON report
    if output_json:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_directory": str(data_dir),
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_outliers": total_outliers,
                "passed": total_errors == 0,
            },
            "schema_validation": {
                r.table_name: {
                    "file": f"{r.table_name}.parquet",
                    "row_count": r.row_count,
                    "passed": r.passed,
                    "errors": r.errors,
                    "warnings": r.warnings,
                }
                for r in results
            },
            "data_quality_checks": all_quality_warnings,
            "statistical_checks": statistical_checks,
            "missing_files": missing_files,
        }

        json_output = json.dumps(report, indent=2)

        if output:
            Path(output).write_text(json_output)
            print(f"Report written to {output}")
        else:
            print(json_output)
    else:
        # Console summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Errors: {total_errors}")
        print(f"Warnings: {total_warnings}")
        if check_outliers:
            print(f"Outliers: {total_outliers}")

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

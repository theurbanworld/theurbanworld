"""
Identify and filter density outlier cities from GHSL data.

Purpose: Some cities in the GHSL/UCDB dataset have unrealistically high population
         densities. These are typically small cities (few H3 cells or grid pixels)
         where the GHSL raster population estimates are concentrated into a tiny area,
         producing densities that exceed any real-world city.

Root cause: GHSL assigns population to ~1km grid cells using satellite-derived built-up
            area and census disaggregation. When a small UCDB boundary captures only a
            handful of these cells—especially near a larger city's dense core—the
            resulting density can be 2-5x higher than the densest real cities (Dhaka,
            Manila at ~25-30K/km²).

Approach: Median-based two-tier filtering
  - Compute each city's MEDIAN density and MEDIAN cell count across all 12 epochs.
    Using medians smooths out early-epoch noise (1975-1990 GHSL data is lower
    resolution, so growing cities may appear artificially tiny/dense at early epochs).
  - Tier 1 (tiny cities): Cities with median cell count below TINY_CELL_COUNT are
    always excluded — persistently too few data points for any meaningful estimate.
  - Tier 2 (small + dense): Cities with median cell count below SMALL_CELL_COUNT AND
    median density above MAX_DENSITY_PER_KM2 are excluded — persistently small cities
    with implausibly high density are data artifacts, not real urban areas.

Thresholds:
  - TINY_CELL_COUNT = 5: ~3.7 km² for H3-R8, ~5 km² for grid-1km. Below this,
    the area is too small for any reliable city-level estimate.
  - SMALL_CELL_COUNT = 50: ~37 km² for H3-R8, ~50 km² for grid-1km. Below this,
    density estimates are unreliable if they exceed the physical limits of real cities.
  - MAX_DENSITY_PER_KM2 = 20,000: The densest real UCDB cities (Mumbai, Dhaka, Manila)
    reach ~25-28K/km² but have hundreds of cells. Small cities with median density
    above 20K are data artifacts.

Usage:
  # As a library (in compute_rankings, web_export)
  from ..cities.density_outliers import filter_density_outliers
  df = filter_density_outliers(df)

  # As a standalone analysis tool
  uv run python -m src.cities.density_outliers --source h3-r8

  # Write a JSON report of excluded cities
  uv run python -m src.cities.density_outliers --source h3-r8 --report

Date: 2026-03-15
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import click
import polars as pl

from ..utils.config import get_processed_path

# =============================================================================
# Thresholds
# =============================================================================

# Tier 1: Tiny cities — always excluded regardless of density.
# H3-R8: 5 cells ≈ 3.7 km². Grid-1km: 5 cells = 5 km².
TINY_CELL_COUNT = 5

# Tier 2: Small cities — excluded only if density exceeds MAX_DENSITY_PER_KM2.
# H3-R8: 50 cells ≈ 37 km². Grid-1km: 50 cells = 50 km².
SMALL_CELL_COUNT = 50

# Maximum plausible median density (people/km²) for small cities.
# Major cities like Mumbai (~28K), Dhaka (~25K) are preserved because they have
# hundreds of cells. Small cities with median density above this are artifacts.
MAX_DENSITY_PER_KM2 = 20_000

# Report output path
REPORT_PATH = Path("data/processed/cities/density_outliers_report.json")


# =============================================================================
# Filtering
# =============================================================================


def identify_outlier_city_ids(
    df: pl.DataFrame,
    tiny_cell_count: int = TINY_CELL_COUNT,
    small_cell_count: int = SMALL_CELL_COUNT,
    max_density: float = MAX_DENSITY_PER_KM2,
) -> set[str]:
    """
    Identify city_ids that are density outliers based on median values across epochs.

    Computes each city's median density and median cell count across all epochs,
    then applies the two-tier filter to these stable summaries. This avoids
    false positives from early-epoch noise (e.g. cities that were tiny in 1975
    but grew into legitimate cities by 2025).

    Two-tier filter on medians:
      - Tier 1: median_cells < tiny_cell_count (always exclude), OR
      - Tier 2: median_cells < small_cell_count AND median_density > max_density

    Args:
        df: Population DataFrame with city_id, epoch, cell_count, density_per_km2
        tiny_cell_count: Tier 1 threshold — always exclude below this
        small_cell_count: Tier 2 threshold — exclude if also above max_density
        max_density: Maximum density threshold for tier 2 (people/km²)

    Returns:
        Set of city_ids to exclude
    """
    city_medians = df.group_by("city_id").agg(
        pl.col("density_per_km2").median().alias("median_density"),
        pl.col("cell_count").median().alias("median_cells"),
    )
    outliers = city_medians.filter(
        (pl.col("median_cells") < tiny_cell_count)
        | (
            (pl.col("median_cells") < small_cell_count)
            & (pl.col("median_density") > max_density)
        )
    )
    return set(outliers["city_id"].to_list())


def filter_density_outliers(
    df: pl.DataFrame,
    tiny_cell_count: int = TINY_CELL_COUNT,
    small_cell_count: int = SMALL_CELL_COUNT,
    max_density: float = MAX_DENSITY_PER_KM2,
    verbose: bool = True,
) -> pl.DataFrame:
    """
    Remove density outlier cities from a population DataFrame.

    Removes all epochs for a city if its median values trigger the outlier criteria.
    This prevents partial time series and ensures consistent city sets across epochs.

    Args:
        df: Population DataFrame with city_id, epoch, cell_count, density_per_km2
        tiny_cell_count: Tier 1 threshold — always exclude below this
        small_cell_count: Tier 2 threshold — exclude if also above max_density
        max_density: Maximum density threshold for tier 2 (people/km²)
        verbose: Print summary of removed cities

    Returns:
        Filtered DataFrame with outlier cities removed
    """
    outlier_ids = identify_outlier_city_ids(df, tiny_cell_count, small_cell_count, max_density)

    if not outlier_ids:
        if verbose:
            print("  No density outliers found")
        return df

    filtered = df.filter(~pl.col("city_id").is_in(outlier_ids))

    if verbose:
        n_before = df["city_id"].n_unique()
        n_after = filtered["city_id"].n_unique()
        print(f"  Density outlier filter: removed {len(outlier_ids)} cities "
              f"({n_before:,} → {n_after:,})")

    return filtered


# =============================================================================
# Report Generation
# =============================================================================


def build_outlier_report(
    pop: pl.DataFrame,
    source: str,
    tiny_cell_count: int,
    small_cell_count: int,
    max_density: float,
    name_map: dict[str, str],
    country_map: dict[str, str],
) -> dict:
    """Build a structured report of excluded cities."""
    outlier_ids = identify_outlier_city_ids(pop, tiny_cell_count, small_cell_count, max_density)

    # Compute medians for outlier cities (used for reason classification)
    city_medians = (
        pop.filter(pl.col("city_id").is_in(outlier_ids))
        .group_by("city_id")
        .agg(
            pl.col("density_per_km2").median().alias("median_density"),
            pl.col("cell_count").median().alias("median_cells"),
        )
    )
    median_map = {
        row["city_id"]: (row["median_density"], row["median_cells"])
        for row in city_medians.to_dicts()
    }

    excluded_cities = []
    for row in (
        pop.filter(pl.col("city_id").is_in(outlier_ids) & (pl.col("epoch") == 2025))
        .sort("density_per_km2", descending=True)
        .to_dicts()
    ):
        cid = row["city_id"]
        med_density, med_cells = median_map.get(cid, (0, 0))
        reasons = []
        if med_cells < tiny_cell_count:
            reasons.append("tiny_city")
        elif med_cells < small_cell_count and med_density > max_density:
            reasons.append("small_city_high_density")

        excluded_cities.append({
            "city_id": cid,
            "name": name_map.get(cid),
            "country": country_map.get(cid),
            "density_per_km2": round(row["density_per_km2"], 1),
            "median_density": round(med_density, 1),
            "population": round(row["population"]),
            "area_km2": round(row["area_km2"], 1),
            "cell_count": row["cell_count"],
            "median_cells": round(med_cells),
            "reasons": reasons,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "method": "median-based two-tier filter",
        "thresholds": {
            "tiny_cell_count": tiny_cell_count,
            "small_cell_count": small_cell_count,
            "max_density_per_km2": max_density,
        },
        "total_cities_before": pop["city_id"].n_unique(),
        "total_excluded": len(excluded_cities),
        "excluded_cities": excluded_cities,
    }


# =============================================================================
# Analysis CLI
# =============================================================================


VALID_SOURCES = ("h3-r8", "grid-1km")


def _source_slug(source: str) -> str:
    return source.replace("-", "_")


def analyze_outliers(
    source: str,
    tiny_cell_count: int,
    small_cell_count: int,
    max_density: float,
    write_report: bool = False,
) -> None:
    """Analyze and report density outliers in the population data."""
    slug = _source_slug(source)
    pop_path = get_processed_path("cities") / f"city_populations_{slug}.parquet"
    cities_path = get_processed_path("cities") / "cities.parquet"

    if not pop_path.exists():
        print(f"ERROR: {pop_path} not found. Run compute_populations first.")
        return

    # Load data
    pop = pl.read_parquet(pop_path)
    print(f"Loaded {pop['city_id'].n_unique():,} cities from {pop_path.name}")

    # Load city names if available
    name_map: dict[str, str] = {}
    country_map: dict[str, str] = {}
    if cities_path.exists():
        cities = pl.read_parquet(cities_path).select(
            ["city_id", "name", "country_name"]
        )
        for row in cities.to_dicts():
            name_map[row["city_id"]] = row["name"] or "???"
            country_map[row["city_id"]] = row["country_name"] or "???"

    # Find outliers
    outlier_ids = identify_outlier_city_ids(pop, tiny_cell_count, small_cell_count, max_density)

    if not outlier_ids:
        print("\nNo outliers found with current thresholds.")
        return

    # Compute medians for display
    city_medians = (
        pop.filter(pl.col("city_id").is_in(outlier_ids))
        .group_by("city_id")
        .agg(
            pl.col("density_per_km2").median().alias("median_density"),
            pl.col("cell_count").median().alias("median_cells"),
        )
    )
    median_map = {
        row["city_id"]: (row["median_density"], row["median_cells"])
        for row in city_medians.to_dicts()
    }

    # Detail each outlier
    print(f"\n{'='*90}")
    print(f"DENSITY OUTLIERS: {len(outlier_ids)} cities (median-based filter)")
    print(f"Thresholds: tiny_cells={tiny_cell_count}, small_cells={small_cell_count}, "
          f"max_density={max_density:,}/km²")
    print(f"{'='*90}")

    # Get 2025 data for outlier cities, sorted by median density
    outlier_data = (
        pop.filter(
            pl.col("city_id").is_in(outlier_ids) & (pl.col("epoch") == 2025)
        )
        .sort("density_per_km2", descending=True)
    )

    print(f"\n{'City ID':>8}  {'Name':30} {'Country':20} {'Med Density':>11} {'Med Cells':>9} "
          f"{'Pop 2025':>12} {'Cells 2025':>10}  Reason")
    print("-" * 130)

    for row in outlier_data.to_dicts():
        cid = row["city_id"]
        name = name_map.get(cid, "???")
        country = country_map.get(cid, "???")
        med_density, med_cells = median_map.get(cid, (0, 0))
        pop_val = row["population"]
        cells = row["cell_count"]

        reasons = []
        if med_cells < tiny_cell_count:
            reasons.append(f"tiny (median_cells={med_cells:.0f})")
        elif med_cells < small_cell_count and med_density > max_density:
            reasons.append(f"small+dense (med_cells={med_cells:.0f}, med_density={med_density:,.0f})")

        print(f"{cid:>8}  {name[:30]:30} {country[:20]:20} {med_density:11,.0f} {med_cells:9.0f} "
              f"{pop_val:12,.0f} {cells:10}  {'; '.join(reasons)}")

    # Summary statistics
    print(f"\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")

    tiny_cities = city_medians.filter(pl.col("median_cells") < tiny_cell_count)
    small_dense = city_medians.filter(
        (pl.col("median_cells") >= tiny_cell_count)
        & (pl.col("median_cells") < small_cell_count)
        & (pl.col("median_density") > max_density)
    )

    print(f"  Tier 1 — tiny cities (median cells < {tiny_cell_count}): "
          f"{tiny_cities.height}")
    print(f"  Tier 2 — small + dense (median cells < {small_cell_count} & median density > {max_density:,}): "
          f"{small_dense.height}")
    print(f"  Total unique cities removed: {len(outlier_ids)}")

    # Show what the top density rankings look like after filtering
    print(f"\n{'='*90}")
    print("TOP 10 DENSEST CITIES AFTER FILTERING (2025)")
    print(f"{'='*90}")

    filtered = filter_density_outliers(
        pop, tiny_cell_count, small_cell_count, max_density, verbose=False
    )
    top_dense = (
        filtered.filter(pl.col("epoch") == 2025)
        .sort("density_per_km2", descending=True)
        .head(10)
    )

    for i, row in enumerate(top_dense.to_dicts(), 1):
        cid = row["city_id"]
        name = name_map.get(cid, "???")
        print(f"  {i:2}. {name[:30]:30} {row['density_per_km2']:10,.0f}/km²  "
              f"pop={row['population']:12,.0f}  area={row['area_km2']:.1f} km²  "
              f"cells={row['cell_count']}")

    # Write JSON report
    if write_report:
        report = build_outlier_report(
            pop, source, tiny_cell_count, small_cell_count, max_density,
            name_map, country_map,
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2))
        print(f"\nReport written to {REPORT_PATH}")


@click.command()
@click.option("--source", default="h3-r8", type=click.Choice(VALID_SOURCES))
@click.option("--tiny-cells", default=TINY_CELL_COUNT, type=int,
              help=f"Tier 1: always exclude below this (default: {TINY_CELL_COUNT})")
@click.option("--small-cells", default=SMALL_CELL_COUNT, type=int,
              help=f"Tier 2: exclude if also above max-density (default: {SMALL_CELL_COUNT})")
@click.option("--max-density", default=MAX_DENSITY_PER_KM2, type=float,
              help=f"Maximum density/km² for tier 2 (default: {MAX_DENSITY_PER_KM2:,})")
@click.option("--report", is_flag=True, help="Write JSON report to data/processed/cities/")
def main(source: str, tiny_cells: int, small_cells: int, max_density: float, report: bool):
    """Analyze density outliers in city population data."""
    print("=" * 90)
    print(f"Density Outlier Analysis (source: {source})")
    print("=" * 90)

    analyze_outliers(source, tiny_cells, small_cells, max_density, write_report=report)


if __name__ == "__main__":
    main()

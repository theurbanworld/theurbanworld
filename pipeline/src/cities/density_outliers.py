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

Approach: Two-tier filtering
  - Tier 1 (tiny cities): Cities with fewer than TINY_CELL_COUNT cells are always
    excluded — too few data points for any meaningful density estimate.
  - Tier 2 (small + dense): Cities with fewer than SMALL_CELL_COUNT cells AND density
    above MAX_DENSITY_PER_KM2 are excluded — small cities claiming to be denser than
    the world's densest major cities are data artifacts, not real urban areas.
  - A city is excluded if it triggers EITHER tier at ANY epoch.

Thresholds:
  - TINY_CELL_COUNT = 5: ~3.7 km² for H3-R8, ~5 km² for grid-1km. Below this,
    the area is too small for any reliable city-level estimate.
  - SMALL_CELL_COUNT = 50: ~37 km² for H3-R8, ~50 km² for grid-1km. Below this,
    density estimates are unreliable if they exceed the physical limits of real cities.
  - MAX_DENSITY_PER_KM2 = 25,000: The densest real UCDB cities (Mumbai, Dhaka, Manila)
    reach ~25-28K/km². Small cities above this threshold are data artifacts.

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

# Maximum plausible density (people/km²) for small cities.
# Major cities like Mumbai (~28K), Dhaka (~25K) are preserved because they have
# hundreds of cells. Small cities above this are data artifacts.
MAX_DENSITY_PER_KM2 = 25_000

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
    Identify city_ids that are density outliers at ANY epoch.

    Two-tier filter — a city is flagged if, at any epoch:
      - Tier 1: cell_count < tiny_cell_count (always exclude), OR
      - Tier 2: cell_count < small_cell_count AND density_per_km2 > max_density

    Args:
        df: Population DataFrame with city_id, epoch, cell_count, density_per_km2
        tiny_cell_count: Tier 1 threshold — always exclude below this
        small_cell_count: Tier 2 threshold — exclude if also above max_density
        max_density: Maximum density threshold for tier 2 (people/km²)

    Returns:
        Set of city_ids to exclude
    """
    outliers = df.filter(
        (pl.col("cell_count") < tiny_cell_count)
        | (
            (pl.col("cell_count") < small_cell_count)
            & (pl.col("density_per_km2") > max_density)
        )
    )
    return set(outliers["city_id"].unique().to_list())


def filter_density_outliers(
    df: pl.DataFrame,
    tiny_cell_count: int = TINY_CELL_COUNT,
    small_cell_count: int = SMALL_CELL_COUNT,
    max_density: float = MAX_DENSITY_PER_KM2,
    verbose: bool = True,
) -> pl.DataFrame:
    """
    Remove density outlier cities from a population DataFrame.

    Removes all epochs for a city if ANY epoch triggers the outlier criteria.
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

    excluded_cities = []
    for row in (
        pop.filter(pl.col("city_id").is_in(outlier_ids) & (pl.col("epoch") == 2025))
        .sort("density_per_km2", descending=True)
        .to_dicts()
    ):
        cid = row["city_id"]
        reasons = []
        if row["cell_count"] < tiny_cell_count:
            reasons.append("tiny_city")
        elif row["cell_count"] < small_cell_count and row["density_per_km2"] > max_density:
            reasons.append("small_city_high_density")

        excluded_cities.append({
            "city_id": cid,
            "name": name_map.get(cid),
            "country": country_map.get(cid),
            "density_per_km2": round(row["density_per_km2"], 1),
            "population": round(row["population"]),
            "area_km2": round(row["area_km2"], 1),
            "cell_count": row["cell_count"],
            "reasons": reasons,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
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

    # Detail each outlier
    print(f"\n{'='*90}")
    print(f"DENSITY OUTLIERS: {len(outlier_ids)} cities")
    print(f"Thresholds: tiny_cells={tiny_cell_count}, small_cells={small_cell_count}, "
          f"max_density={max_density:,}/km²")
    print(f"{'='*90}")

    # Get 2025 data for outlier cities, sorted by density
    outlier_data = (
        pop.filter(
            pl.col("city_id").is_in(outlier_ids) & (pl.col("epoch") == 2025)
        )
        .sort("density_per_km2", descending=True)
    )

    print(f"\n{'City ID':>8}  {'Name':30} {'Country':20} {'Density':>10} {'Pop':>12} "
          f"{'Area km²':>8} {'Cells':>5}  Reason")
    print("-" * 120)

    for row in outlier_data.to_dicts():
        cid = row["city_id"]
        name = name_map.get(cid, "???")
        country = country_map.get(cid, "???")
        density = row["density_per_km2"]
        pop_val = row["population"]
        area = row["area_km2"]
        cells = row["cell_count"]

        reasons = []
        if cells < tiny_cell_count:
            reasons.append(f"tiny (cells={cells} < {tiny_cell_count})")
        elif cells < small_cell_count and density > max_density:
            reasons.append(f"small+dense (cells={cells}, density={density:,.0f})")

        print(f"{cid:>8}  {name[:30]:30} {country[:20]:20} {density:10,.0f} "
              f"{pop_val:12,.0f} {area:8.1f} {cells:5}  {'; '.join(reasons)}")

    # Summary statistics
    print(f"\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")

    epoch_2025 = pop.filter(
        pl.col("city_id").is_in(outlier_ids) & (pl.col("epoch") == 2025)
    )
    tiny_cities = epoch_2025.filter(pl.col("cell_count") < tiny_cell_count)
    small_dense = epoch_2025.filter(
        (pl.col("cell_count") >= tiny_cell_count)
        & (pl.col("cell_count") < small_cell_count)
        & (pl.col("density_per_km2") > max_density)
    )

    print(f"  Tier 1 — tiny cities (cells < {tiny_cell_count}): "
          f"{tiny_cities['city_id'].n_unique()}")
    print(f"  Tier 2 — small + dense (cells < {small_cell_count} & density > {max_density:,}): "
          f"{small_dense['city_id'].n_unique()}")
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

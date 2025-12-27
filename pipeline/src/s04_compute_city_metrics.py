"""
Compute city-level population metrics from H3 cell data.

Purpose: Aggregate H3 population data by city_id for each epoch, computing
         total population, total area (exact), and population density.
Input:
  - data/processed/ghsl_pop_1km/h3_r8_pop_{epoch}.parquet
Output:
  - data/processed/city_metrics/city_metrics.parquet

Output Schema (city_metrics.parquet):
  | Column          | Type    | Description                               |
  |-----------------|---------|-------------------------------------------|
  | city_id         | String  | Primary key from UCDB                     |
  | epoch           | Int64   | Year (1975, 1980, ..., 2030)              |
  | population      | Float64 | Sum of H3 cell populations                |
  | area_km2        | Float64 | Sum of exact H3 cell areas (varies by lat)|
  | density_per_km2 | Float64 | population / area_km2                     |
  | cell_count      | Int64   | Number of H3 cells for this city-epoch    |

Decision log:
  - Uses exact H3 cell areas via h3.cell_area() - cells vary 0.55-0.74 km² by latitude
  - Long format output for flexibility in downstream analysis
  - Aggregates from individual epoch files (contain city_id)
Date: 2024-12-26
"""

import click
import h3
import polars as pl
from pathlib import Path

from .utils.config import config, get_processed_path


def compute_city_metrics_for_epoch(epoch: int, input_dir: Path) -> pl.DataFrame:
    """
    Compute city metrics for a single epoch.

    Args:
        epoch: Year to process (1975, 1980, ..., 2030)
        input_dir: Directory containing h3_r8_pop_{epoch}.parquet files

    Returns:
        DataFrame with city_id, epoch, population, area_km2, density_per_km2, cell_count
    """
    file_path = input_dir / f"h3_r8_pop_{epoch}.parquet"

    if not file_path.exists():
        raise FileNotFoundError(f"Missing: {file_path}")

    # Load H3 population data
    h3_pop = pl.read_parquet(file_path)

    # Compute exact area for each H3 cell using h3.cell_area()
    # h3_index is stored as Int64, need to convert to string hex first
    h3_pop = h3_pop.with_columns(
        pl.col("h3_index")
        .map_elements(
            lambda idx: h3.cell_area(h3.int_to_str(idx), unit="km^2"),
            return_dtype=pl.Float64,
        )
        .alias("area_km2")
    )

    # Aggregate by city_id
    city_metrics = h3_pop.group_by("city_id").agg([
        pl.col("population").sum().alias("population"),
        pl.col("area_km2").sum().alias("area_km2"),
        pl.len().alias("cell_count"),
    ])

    # Add epoch and compute density
    city_metrics = city_metrics.with_columns([
        pl.lit(epoch).alias("epoch"),
        (pl.col("population") / pl.col("area_km2")).alias("density_per_km2"),
    ])

    # Reorder columns
    return city_metrics.select([
        "city_id", "epoch", "population", "area_km2", "density_per_km2", "cell_count"
    ])


def compute_all_city_metrics(epochs: list[int] | None = None) -> pl.DataFrame:
    """
    Compute city metrics for all epochs.

    Args:
        epochs: List of epochs to process (default: all from config)

    Returns:
        Concatenated DataFrame with metrics for all city-epoch combinations
    """
    input_dir = get_processed_path("ghsl_pop_1km")
    epochs = epochs or config.GHSL_POP_EPOCHS

    all_metrics = []
    for epoch in epochs:
        print(f"  Processing epoch {epoch}...")
        metrics = compute_city_metrics_for_epoch(epoch, input_dir)
        total_pop = metrics["population"].sum()
        print(f"    {len(metrics):,} cities, total pop: {total_pop:,.0f}")
        all_metrics.append(metrics)

    return pl.concat(all_metrics)


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
def main(force: bool = False):
    """Compute city-level population metrics from H3 cell data."""
    print("=" * 60)
    print("City Metrics Computation")
    print("=" * 60)

    # Output path
    output_dir = get_processed_path("city_metrics")
    output_path = output_dir / "city_metrics.parquet"

    # Check if output exists
    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    # Compute metrics
    print("\nComputing city metrics (with exact H3 cell areas)...")
    metrics = compute_all_city_metrics()

    # Save
    print(f"\nSaving to {output_path}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics.write_parquet(output_path)

    # Summary
    print("\n" + "=" * 60)
    print("Computation Complete")
    print("=" * 60)
    print(f"Total rows: {len(metrics):,}")
    print(f"Unique cities: {metrics['city_id'].n_unique():,}")
    print(f"Epochs: {sorted(metrics['epoch'].unique().to_list())}")
    print(f"Output: {output_path}")

    # Sample: top 5 cities by 2025 population
    print("\nTop 5 cities by 2025 population:")
    sample = (
        metrics.filter(pl.col("epoch") == 2025)
        .sort("population", descending=True)
        .head(5)
        .select(["city_id", "population", "area_km2", "density_per_km2"])
    )
    print(sample)


if __name__ == "__main__":
    main()

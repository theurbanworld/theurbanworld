"""
Compute city-level population data from grid or H3 cell data.

Purpose: Aggregate population data by city_id for each epoch, computing
         total population, total area, and population density.
Input:
  --source h3-r8:    data/processed/ghsl_h3_r8/h3_r8_pop_{epoch}.parquet
  --source grid-1km: data/processed/ghsl_grid_1km/grid_1km_pop_{epoch}.parquet
Output:
  - data/processed/cities/city_populations_{source}.parquet

Output Schema (city_populations_{source}.parquet):
  | Column          | Type    | Description                               |
  |-----------------|---------|-------------------------------------------|
  | city_id         | String  | Primary key from UCDB                     |
  | epoch           | Int64   | Year (1975, 1980, ..., 2030)              |
  | population      | Float64 | Sum of cell populations                   |
  | area_km2        | Float64 | Sum of cell areas                         |
  | density_per_km2 | Float64 | population / area_km2                     |
  | cell_count      | Int64   | Number of cells for this city-epoch       |

Decision log:
  - H3 source: exact cell areas via h3.cell_area() (0.55-0.74 km² by latitude)
  - Grid source: 1.0 km² per pixel (equal-area Mollweide projection)
  - Long format output for flexibility in downstream analysis
Date: 2025-12-26
"""

from pathlib import Path

import click
import polars as pl

import h3

from ..utils.config import config, get_processed_path

VALID_SOURCES = ("h3-r8", "grid-1km")


def _source_slug(source: str) -> str:
    """Convert CLI source name to filename slug: 'h3-r8' → 'h3_r8'."""
    return source.replace("-", "_")


def compute_h3_population_for_epoch(
    epoch: int, input_dir: Path, canonical_city_ids: set[str] | None = None
) -> pl.DataFrame:
    """Compute city population from H3 cells for a single epoch."""
    file_path = input_dir / f"h3_r8_pop_{epoch}.parquet"
    if not file_path.exists():
        raise FileNotFoundError(f"Missing: {file_path}")

    h3_pop = pl.read_parquet(file_path)

    if canonical_city_ids is not None:
        h3_pop = h3_pop.filter(pl.col("city_id").is_in(canonical_city_ids))

    # Compute exact area for each H3 cell
    h3_pop = h3_pop.with_columns(
        pl.col("h3_index")
        .map_elements(
            lambda idx: h3.cell_area(h3.int_to_str(idx), unit="km^2"),
            return_dtype=pl.Float64,
        )
        .alias("area_km2")
    )

    city_pop = h3_pop.group_by("city_id").agg(
        [
            pl.col("population").sum().alias("population"),
            pl.col("area_km2").sum().alias("area_km2"),
            pl.len().alias("cell_count"),
        ]
    )

    city_pop = city_pop.with_columns(
        [
            pl.lit(epoch).alias("epoch"),
            (pl.col("population") / pl.col("area_km2")).alias("density_per_km2"),
        ]
    )

    return city_pop.select(
        ["city_id", "epoch", "population", "area_km2", "density_per_km2", "cell_count"]
    )


def compute_grid_population_for_epoch(
    epoch: int, input_dir: Path, canonical_city_ids: set[str] | None = None
) -> pl.DataFrame:
    """Compute city population from grid pixels for a single epoch."""
    file_path = input_dir / f"grid_1km_pop_{epoch}.parquet"
    if not file_path.exists():
        raise FileNotFoundError(f"Missing: {file_path}")

    grid_pop = pl.read_parquet(file_path)

    if canonical_city_ids is not None:
        grid_pop = grid_pop.filter(pl.col("city_id").is_in(canonical_city_ids))

    # Each Mollweide 1km pixel = exactly 1.0 km²
    city_pop = grid_pop.group_by("city_id").agg(
        [
            pl.col("population").sum().alias("population"),
            pl.len().alias("cell_count"),
        ]
    )

    city_pop = city_pop.with_columns(
        [
            pl.lit(epoch).alias("epoch"),
            pl.col("cell_count").cast(pl.Float64).alias("area_km2"),
            (pl.col("population") / pl.col("cell_count")).alias("density_per_km2"),
        ]
    )

    return city_pop.select(
        ["city_id", "epoch", "population", "area_km2", "density_per_km2", "cell_count"]
    )


def compute_all_city_populations(source: str, epochs: list[int] | None = None) -> pl.DataFrame:
    """
    Compute city populations for all epochs from specified source.

    Args:
        source: 'h3-r8' or 'grid-1km'
        epochs: List of epochs to process (default: all from config)
    """
    if source == "h3-r8":
        input_dir = get_processed_path("ghsl_h3_r8")
        compute_fn = compute_h3_population_for_epoch
    else:
        input_dir = get_processed_path("ghsl_grid_1km")
        compute_fn = compute_grid_population_for_epoch

    epochs = epochs or config.GHSL_POP_EPOCHS

    # Load canonical city_ids from UCDB-based cities.parquet
    cities_path = get_processed_path("cities") / "cities.parquet"
    canonical_city_ids = set(pl.read_parquet(cities_path).select("city_id").to_series().to_list())
    print(f"  Filtering to {len(canonical_city_ids):,} canonical UCDB city_ids")

    all_pops = []
    for epoch in epochs:
        print(f"  Processing epoch {epoch}...")
        pop_data = compute_fn(epoch, input_dir, canonical_city_ids)
        total_pop = pop_data["population"].sum()
        print(f"    {len(pop_data):,} cities, total pop: {total_pop:,.0f}")
        all_pops.append(pop_data)

    return pl.concat(all_pops)


@click.command()
@click.option("--source", required=True, type=click.Choice(VALID_SOURCES), help="Data source")
@click.option("--force", is_flag=True, help="Overwrite existing output")
def main(source: str, force: bool = False):
    """Compute city-level population data from grid or H3 cell data."""
    slug = _source_slug(source)

    print("=" * 60)
    print(f"City Population Computation (source: {source})")
    print("=" * 60)

    output_dir = get_processed_path("cities")
    output_path = output_dir / f"city_populations_{slug}.parquet"

    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    print(f"\nComputing city populations from {source}...")
    pop_data = compute_all_city_populations(source)

    print(f"\nSaving to {output_path}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    pop_data.write_parquet(output_path)

    print("\n" + "=" * 60)
    print("Computation Complete")
    print("=" * 60)
    print(f"Total rows: {len(pop_data):,}")
    print(f"Unique cities: {pop_data['city_id'].n_unique():,}")
    print(f"Epochs: {sorted(pop_data['epoch'].unique().to_list())}")
    print(f"Output: {output_path}")

    # Sample: top 5 cities by 2025 population
    print("\nTop 5 cities by 2025 population:")
    sample = (
        pop_data.filter(pl.col("epoch") == 2025)
        .sort("population", descending=True)
        .head(5)
        .select(["city_id", "population", "area_km2", "density_per_km2"])
    )
    print(sample)


if __name__ == "__main__":
    main()

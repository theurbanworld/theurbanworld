"""
Compute Bertaud-style radial density profiles.

Purpose: Calculate population density at 1km intervals from city center,
         using population-weighted centroids and exact H3 cell areas.
Input:
  - data/processed/ghsl_pop_1km/h3_r8_pop_{epoch}.parquet
Output:
  - data/processed/radial_profiles/radial_profiles.parquet

Output Schema (radial_profiles.parquet):
  | Column          | Type    | Description                               |
  |-----------------|---------|-------------------------------------------|
  | city_id         | String  | Primary key from UCDB                     |
  | epoch           | Int64   | Year (1975, 1980, ..., 2030)              |
  | ring_index      | Int64   | Ring number (0-49 for 0-50km)             |
  | distance_min_km | Float64 | Ring start distance from centroid         |
  | distance_max_km | Float64 | Ring end distance from centroid           |
  | population      | Float64 | Sum of H3 cell populations in ring        |
  | area_km2        | Float64 | Sum of exact H3 cell areas in ring        |
  | density_per_km2 | Float64 | population / area_km2                     |
  | cell_count      | Int64   | Number of H3 cells in ring                |

Decision log:
  - Population-weighted centroid for each city-epoch (3D Cartesian averaging)
  - 50 rings at 1km intervals (0-50km max distance)
  - Exact H3 cell areas via h3.cell_area() - varies by latitude
  - Empty rings included with population=0, area=0, density=null
Date: 2025-12-27
"""

import click
import h3
import polars as pl
from pathlib import Path

from .utils.config import config, get_processed_path
from .utils.h3_utils import (
    assign_cells_to_rings,
    compute_population_weighted_centroid,
    h3_cell_area_km2,
)


def compute_radial_profiles_for_epoch(epoch: int, input_dir: Path) -> pl.DataFrame:
    """
    Compute radial profiles for all cities in a single epoch.

    Args:
        epoch: Year to process (1975, 1980, ..., 2030)
        input_dir: Directory containing h3_r8_pop_{epoch}.parquet files

    Returns:
        DataFrame with radial profile data for all cities
    """
    file_path = input_dir / f"h3_r8_pop_{epoch}.parquet"

    if not file_path.exists():
        raise FileNotFoundError(f"Missing: {file_path}")

    # Load H3 population data
    h3_pop = pl.read_parquet(file_path)

    # Get unique cities
    city_ids = h3_pop["city_id"].unique().to_list()

    all_profiles = []
    for city_id in city_ids:
        city_cells = h3_pop.filter(pl.col("city_id") == city_id)

        if len(city_cells) == 0:
            continue

        # Convert to dict for processing
        h3_indices = city_cells["h3_index"].to_list()
        populations = city_cells["population"].to_list()

        # Convert int64 h3 indices to strings for h3 library
        cells_str = [h3.int_to_str(idx) for idx in h3_indices]
        pop_dict = dict(zip(cells_str, populations))

        # Compute population-weighted centroid
        total_pop = sum(populations)
        if total_pop <= 0:
            continue

        center_lat, center_lng = compute_population_weighted_centroid(cells_str, pop_dict)

        # Assign cells to rings
        rings = assign_cells_to_rings(
            cells=cells_str,
            center_lat=center_lat,
            center_lng=center_lng,
            ring_width_km=config.RADIAL_RING_WIDTH_KM,
            max_radius_km=config.RADIAL_MAX_DISTANCE_KM,
        )

        # Aggregate each ring
        for ring_idx in range(config.RADIAL_NUM_RINGS):
            ring_cells = rings.get(ring_idx, [])

            if len(ring_cells) == 0:
                # Empty ring
                all_profiles.append({
                    "city_id": city_id,
                    "epoch": epoch,
                    "ring_index": ring_idx,
                    "distance_min_km": ring_idx * config.RADIAL_RING_WIDTH_KM,
                    "distance_max_km": (ring_idx + 1) * config.RADIAL_RING_WIDTH_KM,
                    "population": 0.0,
                    "area_km2": 0.0,
                    "density_per_km2": None,
                    "cell_count": 0,
                })
            else:
                ring_pop = sum(pop_dict.get(cell, 0) for cell in ring_cells)
                ring_area = sum(h3_cell_area_km2(cell) for cell in ring_cells)
                ring_density = ring_pop / ring_area if ring_area > 0 else None

                all_profiles.append({
                    "city_id": city_id,
                    "epoch": epoch,
                    "ring_index": ring_idx,
                    "distance_min_km": ring_idx * config.RADIAL_RING_WIDTH_KM,
                    "distance_max_km": (ring_idx + 1) * config.RADIAL_RING_WIDTH_KM,
                    "population": ring_pop,
                    "area_km2": ring_area,
                    "density_per_km2": ring_density,
                    "cell_count": len(ring_cells),
                })

    if not all_profiles:
        return pl.DataFrame(schema={
            "city_id": pl.Utf8,
            "epoch": pl.Int64,
            "ring_index": pl.Int64,
            "distance_min_km": pl.Float64,
            "distance_max_km": pl.Float64,
            "population": pl.Float64,
            "area_km2": pl.Float64,
            "density_per_km2": pl.Float64,
            "cell_count": pl.Int64,
        })

    return pl.DataFrame(all_profiles)


def compute_all_radial_profiles(epochs: list[int] | None = None) -> pl.DataFrame:
    """
    Compute radial profiles for all epochs.

    Args:
        epochs: List of epochs to process (default: all from config)

    Returns:
        Concatenated DataFrame with profiles for all city-epoch combinations
    """
    input_dir = get_processed_path("ghsl_pop_1km")
    epochs = epochs or config.GHSL_POP_EPOCHS

    all_profiles = []
    for epoch in epochs:
        print(f"  Processing epoch {epoch}...")
        profiles = compute_radial_profiles_for_epoch(epoch, input_dir)
        n_cities = profiles["city_id"].n_unique()
        print(f"    {n_cities:,} cities processed")
        all_profiles.append(profiles)

    return pl.concat(all_profiles)


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
def main(force: bool = False):
    """Compute Bertaud-style radial density profiles for all cities."""
    print("=" * 60)
    print("Radial Profile Computation")
    print("=" * 60)

    # Output path
    output_dir = get_processed_path("radial_profiles")
    output_path = output_dir / "radial_profiles.parquet"

    # Check if output exists
    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    # Compute profiles
    print("\nComputing radial density profiles...")
    print(f"  Ring width: {config.RADIAL_RING_WIDTH_KM} km")
    print(f"  Max distance: {config.RADIAL_MAX_DISTANCE_KM} km")
    print(f"  Num rings: {config.RADIAL_NUM_RINGS}")
    print()

    profiles = compute_all_radial_profiles()

    # Save
    print(f"\nSaving to {output_path}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    profiles.write_parquet(output_path)

    # Summary
    print("\n" + "=" * 60)
    print("Computation Complete")
    print("=" * 60)
    print(f"Total rows: {len(profiles):,}")
    print(f"Unique cities: {profiles['city_id'].n_unique():,}")
    print(f"Epochs: {sorted(profiles['epoch'].unique().to_list())}")
    print(f"Output: {output_path}")

    # Sample: ring 0 (0-1km) stats for 2025
    print("\nRing 0 (0-1km) stats for 2025:")
    sample = (
        profiles.filter((pl.col("epoch") == 2025) & (pl.col("ring_index") == 0))
        .select(["population", "area_km2", "density_per_km2"])
        .describe()
    )
    print(sample)


if __name__ == "__main__":
    main()

"""
06 - Compute Bertaud-style radial density profiles.

Purpose: Calculate population density at 1km intervals from city center
Input:
  - data/interim/cities.parquet
  - data/processed/h3_tiles/h3_pop_2020_res9.parquet
  - data/interim/city_boundaries/{city_id}.parquet
Output:
  - data/interim/radial_profiles/{city_id}.json
  - data/interim/radial_profiles/_all_profiles.parquet

Decision log:
  - Use population-weighted centroid from boundary extraction
  - 50 rings at 1km intervals (0-50km)
  - Use H3 res-9 cells (same as boundaries for consistency)
  - Calculate actual area per ring (handles partial/coastal rings)
  - Fit log-linear gradient for urban form classification
Date: 2024-12-08
"""

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import click
import numpy as np
import polars as pl
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_processed_path
from .utils.h3_utils import (
    assign_cells_to_rings,
    cells_within_radius,
    h3_cell_area_km2,
    h3_cell_to_latlng,
    haversine_km,
)
from .utils.progress import ProgressTracker


@dataclass
class RingData:
    """Data for a single concentric ring."""

    ring_index: int
    inner_radius_km: float
    outer_radius_km: float
    center_radius_km: float
    population: int
    area_km2: float
    density_per_km2: float
    cell_count: int
    coverage_fraction: float


@dataclass
class RadialProfile:
    """Complete radial density profile for a city."""

    city_id: str
    centroid_lat: float
    centroid_lng: float
    rings: list[RingData]
    total_population: int
    max_populated_radius_km: float
    gradient_slope: float
    gradient_intercept: float
    gradient_r_squared: float
    is_monocentric: bool


def load_city_centroid(city_id: str, boundaries_dir: Path) -> tuple[float, float] | None:
    """Load centroid from boundary progress file."""
    progress_file = boundaries_dir / "_progress.json"
    if not progress_file.exists():
        return None

    progress = json.loads(progress_file.read_text())
    item = progress.get("items", {}).get(city_id, {})

    if item.get("status") == "complete":
        return item.get("centroid_lat"), item.get("centroid_lng")
    return None


def calculate_ring_density(
    ring_cells: list[str],
    population_grid: dict[str, float],
    inner_radius_km: float,
    outer_radius_km: float,
    ring_index: int,
) -> RingData:
    """Calculate density metrics for a single ring."""
    # Theoretical ring area
    theoretical_area = math.pi * (outer_radius_km**2 - inner_radius_km**2)

    # Actual area and population
    total_pop = 0
    actual_area = 0.0

    for cell in ring_cells:
        total_pop += population_grid.get(cell, 0)
        actual_area += h3_cell_area_km2(cell)

    # Coverage fraction
    coverage = actual_area / theoretical_area if theoretical_area > 0 else 0

    # Density
    density = total_pop / actual_area if actual_area > 0 else 0

    return RingData(
        ring_index=ring_index,
        inner_radius_km=inner_radius_km,
        outer_radius_km=outer_radius_km,
        center_radius_km=(inner_radius_km + outer_radius_km) / 2,
        population=int(total_pop),
        area_km2=actual_area,
        density_per_km2=density,
        cell_count=len(ring_cells),
        coverage_fraction=coverage,
    )


def fit_density_gradient(rings: list[RingData]) -> tuple[float, float, float]:
    """
    Fit log-linear density gradient.

    Model: ln(density) = intercept + slope * distance

    Returns:
        (slope, intercept, r_squared)
    """
    # Filter to rings with population
    valid = [(r.center_radius_km, r.density_per_km2) for r in rings if r.density_per_km2 > 0]

    if len(valid) < 5:
        return 0.0, 0.0, 0.0

    x = np.array([v[0] for v in valid])
    y = np.log(np.array([v[1] for v in valid]))

    # Simple OLS
    n = len(x)
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    slope = numerator / denominator if denominator > 0 else 0
    intercept = y_mean - slope * x_mean

    # R-squared
    y_pred = intercept + slope * x
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return slope, intercept, r_squared


def compute_radial_profile(
    city_id: str,
    centroid: tuple[float, float],
    population_grid: dict[str, float],
    ring_width_km: float = 1.0,
    max_radius_km: float = 50.0,
    h3_resolution: int = 9,
) -> RadialProfile:
    """
    Compute Bertaud-style radial density profile.

    Args:
        city_id: City identifier
        centroid: (lat, lng) of city center
        population_grid: H3 cell -> population mapping
        ring_width_km: Width of each ring
        max_radius_km: Maximum radius to analyze
        h3_resolution: H3 resolution to use

    Returns:
        RadialProfile with all metrics
    """
    center_lat, center_lng = centroid
    num_rings = int(max_radius_km / ring_width_km)

    # Get all cells within max radius
    all_cells = cells_within_radius(center_lat, center_lng, max_radius_km, h3_resolution)

    # Filter to cells with population
    pop_cells = {c for c in all_cells if population_grid.get(c, 0) > 0}

    # Assign to rings
    ring_assignments = assign_cells_to_rings(
        pop_cells, center_lat, center_lng, ring_width_km, max_radius_km
    )

    # Calculate ring metrics
    rings = []
    total_pop = 0
    max_populated_radius = 0.0

    for ring_idx in range(num_rings):
        inner_r = ring_idx * ring_width_km
        outer_r = (ring_idx + 1) * ring_width_km

        ring_data = calculate_ring_density(
            ring_assignments.get(ring_idx, []),
            population_grid,
            inner_r,
            outer_r,
            ring_idx,
        )

        rings.append(ring_data)
        total_pop += ring_data.population

        if ring_data.population > 0:
            max_populated_radius = outer_r

    # Fit gradient
    slope, intercept, r_squared = fit_density_gradient(rings)

    # Classify urban form
    is_monocentric = slope < -0.05  # Negative slope indicates monocentric

    return RadialProfile(
        city_id=city_id,
        centroid_lat=center_lat,
        centroid_lng=center_lng,
        rings=rings,
        total_population=total_pop,
        max_populated_radius_km=max_populated_radius,
        gradient_slope=slope,
        gradient_intercept=intercept,
        gradient_r_squared=r_squared,
        is_monocentric=is_monocentric,
    )


def profile_to_dict(profile: RadialProfile) -> dict:
    """Convert profile to JSON-serializable dict."""
    return {
        "city_id": profile.city_id,
        "centroid": {
            "lat": profile.centroid_lat,
            "lng": profile.centroid_lng,
        },
        "rings": [asdict(r) for r in profile.rings],
        "total_population": profile.total_population,
        "max_populated_radius_km": profile.max_populated_radius_km,
        "gradient": {
            "slope": profile.gradient_slope,
            "intercept": profile.gradient_intercept,
            "r_squared": profile.gradient_r_squared,
        },
        "is_monocentric": profile.is_monocentric,
    }


@click.command()
@click.option("--test-only", is_flag=True, help="Process only test cities")
def main(test_only: bool = False):
    """Compute Bertaud-style radial density profiles."""
    print("=" * 60)
    print("Radial Density Profile Computation")
    print("=" * 60)

    # Load cities
    cities_path = get_interim_path() / "cities.parquet"

    if not cities_path.exists():
        print(f"ERROR: Cities file not found: {cities_path}")
        return

    cities_df = pl.read_parquet(cities_path)

    if test_only:
        from .utils.config import config
        cities_df = cities_df.filter(pl.col("city_id").is_in([str(id) for id in config.TEST_CITY_IDS]))
        print(f"Filtering to {len(cities_df)} test cities")

    print(f"Loaded {len(cities_df)} cities")

    # Load population grid
    pop_path = get_processed_path("h3_tiles") / "h3_pop_2020_res9.parquet"
    if not pop_path.exists():
        print(f"ERROR: Population grid not found: {pop_path}")
        return

    print("Loading population grid...")
    pop_df = pl.read_parquet(pop_path)
    population_grid = dict(zip(pop_df["h3_index"].to_list(), pop_df["population"].to_list()))
    print(f"  Loaded {len(population_grid):,} H3 cells")

    # Initialize progress
    output_dir = get_interim_path("radial_profiles")
    progress_file = output_dir / "_progress.json"
    progress = ProgressTracker(progress_file)

    boundaries_dir = get_interim_path("city_boundaries")

    city_ids = cities_df["city_id"].to_list()
    progress.initialize(city_ids)

    # Process cities
    print(f"\nComputing profiles for {len(cities_df)} cities...")
    all_profiles = []

    for row in tqdm(cities_df.iter_rows(named=True), total=len(cities_df), desc="Cities"):
        city_id = row["city_id"]

        if progress.is_complete(city_id):
            continue

        progress.mark_in_progress(city_id)

        # Get centroid
        centroid = load_city_centroid(city_id, boundaries_dir)
        if not centroid or centroid[0] is None:
            # Fall back to city metadata
            centroid = (row["latitude"], row["longitude"])

        try:
            # Compute profile
            profile = compute_radial_profile(
                city_id,
                centroid,
                population_grid,
                ring_width_km=config.RADIAL_RING_WIDTH_KM,
                max_radius_km=config.RADIAL_MAX_DISTANCE_KM,
                h3_resolution=config.H3_RESOLUTION_MAP,
            )

            # Save JSON
            output_path = output_dir / f"{city_id}.json"
            profile_dict = profile_to_dict(profile)
            output_path.write_text(json.dumps(profile_dict, indent=2))

            # Track for summary
            all_profiles.append({
                "city_id": city_id,
                "total_population": profile.total_population,
                "max_radius_km": profile.max_populated_radius_km,
                "gradient_slope": profile.gradient_slope,
                "is_monocentric": profile.is_monocentric,
            })

            progress.mark_complete(city_id, {
                "total_population": profile.total_population,
                "gradient_slope": round(profile.gradient_slope, 4),
            })

        except Exception as e:
            progress.mark_failed(city_id, str(e))
            print(f"\n  ERROR on {city_id}: {e}")

    # Save summary parquet
    if all_profiles:
        summary_df = pl.DataFrame(all_profiles)
        summary_path = output_dir / "_all_profiles.parquet"
        summary_df.write_parquet(summary_path)
        print(f"\nSaved summary to {summary_path}")

    # Mark completion
    sentinel = output_dir / ".complete"
    sentinel.touch()

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    progress.print_summary()

    if all_profiles:
        mono_count = sum(1 for p in all_profiles if p["is_monocentric"])
        print(f"Monocentric cities: {mono_count}/{len(all_profiles)}")


if __name__ == "__main__":
    main()

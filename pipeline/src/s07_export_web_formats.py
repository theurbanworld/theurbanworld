"""
07 - Export web-ready formats for frontend.

Purpose: Generate final JSON and GeoParquet files for web serving
Input:
  - data/interim/cities.parquet
  - data/interim/h3_pop_1km/time_series.parquet
  - data/interim/city_boundaries/{city_id}.parquet
  - data/interim/radial_profiles/{city_id}.json
  - data/processed/h3_tiles/h3_pop_2025_res9.parquet
Output:
  - data/processed/cities/{city_id}.json (per-city files)
  - data/processed/city_index.json (search index)
  - data/processed/h3_tiles/h3_pop_2025_res9.geoparquet (with geometry)

Decision log:
  - City JSONs contain all data for single-city views
  - City index is lightweight for search/autocomplete
  - H3 boundaries stored as cell ID arrays (efficient encoding)
  - Include metadata for data provenance
Date: 2024-12-08
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import click
import polars as pl
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_processed_path
from .utils.progress import ProgressTracker


def load_time_series(h3_index: str, time_series_df: pl.DataFrame) -> list[dict] | None:
    """Load time series data for H3 cells near a city."""
    # This is a simplified version - in practice you'd aggregate
    # cells within the city boundary
    return None  # Will be computed from boundary cells


def load_boundary_cells(city_id: str, boundaries_dir: Path) -> list[str] | None:
    """Load boundary H3 cells for a city."""
    boundary_file = boundaries_dir / f"{city_id}.parquet"
    if not boundary_file.exists():
        return None

    df = pl.read_parquet(boundary_file)
    return df["h3_index"].to_list()


def load_radial_profile(city_id: str, profiles_dir: Path) -> dict | None:
    """Load radial profile for a city."""
    profile_file = profiles_dir / f"{city_id}.json"
    if not profile_file.exists():
        return None

    return json.loads(profile_file.read_text())


def compute_city_time_series(
    boundary_cells: list[str],
    time_series_df: pl.DataFrame,
) -> list[dict]:
    """
    Compute aggregate time series for a city from its boundary cells.

    Args:
        boundary_cells: List of H3 cell IDs in city boundary
        time_series_df: Wide-format time series data

    Returns:
        List of {year, population} dicts
    """
    if not boundary_cells or time_series_df is None:
        return []

    # Filter to boundary cells
    city_data = time_series_df.filter(pl.col("h3_index").is_in(boundary_cells))

    if len(city_data) == 0:
        return []

    # Sum across all cells for each year
    result = []
    for col in city_data.columns:
        if col.startswith("pop_"):
            year = int(col.replace("pop_", ""))
            total = city_data[col].sum()
            if total and total > 0:
                result.append({"year": year, "population": int(total)})

    return sorted(result, key=lambda x: x["year"])


def build_city_json(
    city: dict,
    boundary_cells: list[str] | None,
    time_series: list[dict],
    radial_profile: dict | None,
) -> dict:
    """
    Build complete city JSON structure.

    Args:
        city: City metadata from urban_centers
        boundary_cells: List of H3 cell IDs
        time_series: Population time series
        radial_profile: Radial density profile

    Returns:
        Complete city JSON dict
    """
    # Simplify radial profile for export
    profile_export = None
    if radial_profile:
        profile_export = {
            "centroid": radial_profile.get("centroid"),
            "rings": [
                {
                    "distance_km": r["center_radius_km"],
                    "density_per_km2": round(r["density_per_km2"], 1),
                    "population": r["population"],
                }
                for r in radial_profile.get("rings", [])
                if r["population"] > 0
            ],
            "gradient_slope": round(radial_profile.get("gradient", {}).get("slope", 0), 4),
            "is_monocentric": radial_profile.get("is_monocentric", False),
        }

    return {
        "id": city["city_id"],
        "name": city["name"],
        "country": city["country_code"],
        "location": {
            "lat": city["latitude"],
            "lon": city["longitude"],
        },
        "population_2025": city["population_2025"],
        "area_km2": round(city["area_km2"], 2),
        "boundary_h3": {
            "resolution": config.H3_RESOLUTION_MAP,
            "cells": boundary_cells or [],
            "cell_count": len(boundary_cells) if boundary_cells else 0,
        },
        "time_series": time_series,
        "radial_profile": profile_export,
        "statistics": {
            "density_avg": round(
                city["population_2025"] / city["area_km2"], 1
            ) if city["area_km2"] > 0 else 0,
        },
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": f"GHS-POP {config.GHSL_POP_RELEASE}",
            "pipeline_version": "0.1.0",
        },
    }


def build_city_index(cities_df: pl.DataFrame) -> dict:
    """
    Build lightweight city index for search.

    Args:
        cities_df: Full cities dataframe

    Returns:
        City index dict
    """
    cities = []
    for row in cities_df.sort("population_2025", descending=True).iter_rows(named=True):
        cities.append({
            "id": row["city_id"],
            "name": row["name"],
            "country": row["country_code"],
            "population": row["population_2025"],
            "lat": round(row["latitude"], 4),
            "lon": round(row["longitude"], 4),
        })

    return {
        "cities": cities,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": f"GHS-UCDB {config.GHSL_UCDB_RELEASE}",
            "total_count": len(cities),
        },
    }


@click.command()
@click.option("--test-only", is_flag=True, help="Export only test cities")
def main(test_only: bool = False):
    """Export web-ready formats."""
    print("=" * 60)
    print("Web Format Export")
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

    # Load time series
    time_series_path = get_interim_path("h3_pop_1km") / "time_series.parquet"
    time_series_df = None
    if time_series_path.exists():
        print("Loading time series...")
        time_series_df = pl.read_parquet(time_series_path)

    # Paths
    boundaries_dir = get_interim_path("city_boundaries")
    profiles_dir = get_interim_path("radial_profiles")
    output_dir = get_processed_path("cities")

    # Initialize progress
    progress_file = output_dir / "_progress.json"
    progress = ProgressTracker(progress_file)

    city_ids = cities_df["city_id"].to_list()
    progress.initialize(city_ids)

    # Export per-city JSONs
    print(f"\nExporting {len(cities_df)} city files...")

    for row in tqdm(cities_df.iter_rows(named=True), total=len(cities_df), desc="Cities"):
        city_id = row["city_id"]

        if progress.is_complete(city_id):
            continue

        progress.mark_in_progress(city_id)

        try:
            # Load components
            boundary_cells = load_boundary_cells(city_id, boundaries_dir)
            radial_profile = load_radial_profile(city_id, profiles_dir)

            # Compute time series
            time_series = []
            if boundary_cells and time_series_df is not None:
                time_series = compute_city_time_series(boundary_cells, time_series_df)

            # Build JSON
            city_json = build_city_json(row, boundary_cells, time_series, radial_profile)

            # Save
            output_path = output_dir / f"{city_id}.json"
            output_path.write_text(json.dumps(city_json, indent=2))

            progress.mark_complete(city_id, {
                "boundary_cells": len(boundary_cells) if boundary_cells else 0,
                "time_series_years": len(time_series),
            })

        except Exception as e:
            progress.mark_failed(city_id, str(e))
            print(f"\n  ERROR on {city_id}: {e}")

    # Build city index
    print("\nBuilding city index...")
    index = build_city_index(cities_df)
    index_path = get_processed_path() / "city_index.json"
    index_path.write_text(json.dumps(index, indent=2))
    print(f"  Saved to {index_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    progress.print_summary()
    print(f"\nCity index: {len(index['cities'])} cities")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()

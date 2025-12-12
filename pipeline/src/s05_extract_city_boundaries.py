"""
05 - Extract city boundaries as H3 cell sets.

Purpose: Define each city's spatial extent as a set of H3 cells
Input:
  - data/interim/cities.parquet
  - data/interim/ucdb/geometries.parquet
  - data/processed/h3_tiles/h3_r9_pop_2025.parquet
Output:
  - data/interim/city_boundaries/{city_id}.parquet

Decision log:
  - Use UCDB polygon + population threshold to define boundaries
  - Include cells with population >= 100 (captures urban fringe)
  - Extract largest connected component to handle fragmentation
  - Fill interior holes using flood-fill inversion
  - Parallel processing with ThreadPoolExecutor (cities are independent)
Date: 2024-12-08
"""

from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import click
import geopandas as gpd
import h3
import polars as pl
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_processed_path
from .utils.h3_utils import (
    compute_population_weighted_centroid,
    get_h3_neighbors,
    h3_cell_area_km2,
    polygon_to_h3_cells,
)
from .utils.progress import ProgressTracker


def load_population_grid(h3_path: Path) -> dict[str, float]:
    """Load H3 population data as dictionary for fast lookups."""
    df = pl.read_parquet(h3_path)
    return dict(zip(df["h3_index"].to_list(), df["population"].to_list()))


def extract_largest_connected_component(cells: set[str]) -> set[str]:
    """
    Find largest spatially connected component using BFS.

    H3 cells are neighbors if they share an edge (k=1 ring).
    """
    if not cells:
        return set()

    visited = set()
    components = []

    for start_cell in cells:
        if start_cell in visited:
            continue

        # BFS from this cell
        component = set()
        queue = deque([start_cell])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            if current in cells:
                component.add(current)
                # Get neighbors
                neighbors = get_h3_neighbors(current)
                for neighbor in neighbors:
                    if neighbor not in visited and neighbor in cells:
                        queue.append(neighbor)

        if component:
            components.append(component)

    # Return largest component
    return max(components, key=len) if components else set()


def fill_boundary_holes(cells: set[str], max_hole_cells: int = 100) -> tuple[set[str], int]:
    """
    Fill interior holes in the boundary using flood-fill inversion.

    Args:
        cells: Set of boundary cells
        max_hole_cells: Maximum hole size to fill (prevents filling large water bodies)

    Returns:
        Tuple of (filled_cells, number_of_holes_filled)
    """
    if not cells or len(cells) < 10:
        return cells, 0

    # Get bounding box of cells
    all_latlngs = [h3.cell_to_latlng(c) for c in cells]
    min_lat = min(ll[0] for ll in all_latlngs) - 0.05
    max_lat = max(ll[0] for ll in all_latlngs) + 0.05
    min_lng = min(ll[1] for ll in all_latlngs) - 0.05
    max_lng = max(ll[1] for ll in all_latlngs) + 0.05

    # Get resolution from first cell
    res = h3.get_resolution(list(cells)[0])

    # Create bounding box polygon and get all cells in it
    from shapely import box
    bbox_polygon = box(min_lng, min_lat, max_lng, max_lat)

    try:
        universe_cells = polygon_to_h3_cells(bbox_polygon, res)
    except Exception:
        # If polygon conversion fails, skip hole filling
        return cells, 0

    if not universe_cells:
        return cells, 0

    # Find exterior cells (flood fill from corners)
    # Start from cells in universe that are not in our boundary
    exterior_start = universe_cells - cells

    # BFS flood fill from exterior
    exterior = set()
    visited = set()
    queue = deque(exterior_start)

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        if current in cells:
            continue  # Stop at boundary

        if current in universe_cells:
            exterior.add(current)
            neighbors = get_h3_neighbors(current)
            for neighbor in neighbors:
                if neighbor not in visited and neighbor in universe_cells:
                    queue.append(neighbor)

    # Holes = cells in universe that are not in boundary and not exterior
    potential_holes = universe_cells - cells - exterior

    # Only fill small holes
    if len(potential_holes) <= max_hole_cells:
        filled = cells | potential_holes
        holes_count = len(potential_holes)
    else:
        filled = cells
        holes_count = 0

    return filled, holes_count


def extract_city_boundary(
    city_id: str,
    city_polygon,
    population_grid: dict[str, float],
    h3_resolution: int = 9,
    population_threshold: int = 100,
    min_cells: int = 10,
) -> dict | None:
    """
    Extract H3 boundary for a single city.

    Args:
        city_id: Unique city identifier
        city_polygon: Shapely polygon for city (WGS84)
        population_grid: H3 cell -> population mapping
        h3_resolution: Target H3 resolution
        population_threshold: Min population per cell
        min_cells: Min cells for valid boundary

    Returns:
        Dict with boundary data or None if failed
    """
    try:
        # Step 1: Get all H3 cells from polygon
        initial_cells = polygon_to_h3_cells(city_polygon, h3_resolution)

        if not initial_cells:
            return None

        # Step 2: Filter by population threshold
        populated_cells = {
            cell for cell in initial_cells
            if population_grid.get(cell, 0) >= population_threshold
        }

        # Handle small cities
        if len(populated_cells) < min_cells:
            # Fall back to any population
            populated_cells = {
                cell for cell in initial_cells
                if population_grid.get(cell, 0) > 0
            }

        if len(populated_cells) < min_cells:
            # Use all polygon cells
            populated_cells = initial_cells

        # Step 3: Extract largest connected component
        connected_cells = extract_largest_connected_component(populated_cells)

        if len(connected_cells) < min_cells:
            connected_cells = populated_cells

        # Step 4: Fill holes
        filled_cells, holes_filled = fill_boundary_holes(connected_cells)

        # Step 5: Calculate metrics
        total_pop = sum(population_grid.get(c, 0) for c in filled_cells)
        total_area = sum(h3_cell_area_km2(c) for c in filled_cells)

        # Step 6: Calculate population-weighted centroid
        centroid_lat, centroid_lng = compute_population_weighted_centroid(
            filled_cells, population_grid
        )

        return {
            "city_id": city_id,
            "h3_cells": list(filled_cells),
            "cell_count": len(filled_cells),
            "total_population": int(total_pop),
            "area_km2": total_area,
            "centroid_lat": centroid_lat,
            "centroid_lng": centroid_lng,
            "holes_filled": holes_filled,
            "resolution": h3_resolution,
        }

    except Exception as e:
        print(f"    Error processing {city_id}: {e}")
        return None


def process_city_batch(
    batch: list[dict],
    geometries: gpd.GeoDataFrame,
    population_grid: dict[str, float],
    output_dir: Path,
    progress: ProgressTracker,
) -> int:
    """Process a batch of cities."""
    processed = 0

    for city in batch:
        city_id = city["city_id"]

        if progress.is_complete(city_id):
            continue

        progress.mark_in_progress(city_id)

        # Get geometry by ID_UC_G0
        geom_row = geometries[geometries["ID_UC_G0"] == int(city_id)]
        if len(geom_row) == 0:
            progress.mark_failed(city_id, "Geometry not found")
            continue
        geom = geom_row.iloc[0].geometry

        # Extract boundary
        result = extract_city_boundary(
            city_id,
            geom,
            population_grid,
            h3_resolution=config.H3_RESOLUTION_MAP,
            population_threshold=config.BOUNDARY_POPULATION_THRESHOLD,
            min_cells=config.BOUNDARY_MIN_CELLS,
        )

        if result:
            # Save boundary
            output_path = output_dir / f"{city_id}.parquet"
            df = pl.DataFrame({
                "h3_index": result["h3_cells"],
            })
            df.write_parquet(output_path)

            # Save metadata
            meta = {k: v for k, v in result.items() if k != "h3_cells"}
            progress.mark_complete(city_id, meta)
            processed += 1
        else:
            progress.mark_failed(city_id, "Boundary extraction failed")

    return processed


@click.command()
@click.option("--test-only", is_flag=True, help="Process only test cities")
@click.option("--workers", default=8, help="Number of parallel workers")
def main(test_only: bool = False, workers: int = 8):
    """Extract city boundaries as H3 cell sets."""
    print("=" * 60)
    print("City Boundary Extraction")
    print("=" * 60)

    # Load data
    cities_path = get_interim_path() / "cities.parquet"

    if not cities_path.exists():
        print(f"ERROR: Cities file not found: {cities_path}")
        return

    cities_df = pl.read_parquet(cities_path)

    if test_only:
        cities_df = cities_df.filter(pl.col("city_id").is_in([str(id) for id in config.TEST_CITY_IDS]))
        print(f"Filtering to {len(cities_df)} test cities")

    print(f"Loaded {len(cities_df)} cities")

    # Load geometries
    geom_path = get_interim_path("ucdb") / "geometries.parquet"
    if not geom_path.exists():
        print(f"ERROR: Geometries not found: {geom_path}")
        return

    print("Loading geometries...")
    geometries = gpd.read_parquet(geom_path)

    # Load population grid
    pop_path = get_processed_path("h3_tiles") / "h3_r9_pop_2025.parquet"
    if not pop_path.exists():
        print(f"ERROR: Population grid not found: {pop_path}")
        return

    print("Loading population grid...")
    population_grid = load_population_grid(pop_path)
    print(f"  Loaded {len(population_grid):,} H3 cells")

    # Initialize progress
    output_dir = get_interim_path("city_boundaries")
    progress_file = output_dir / "_progress.json"
    progress = ProgressTracker(progress_file)

    city_ids = cities_df["city_id"].to_list()
    progress.initialize(city_ids)

    # Process cities
    print(f"\nProcessing {len(cities_df)} cities...")
    cities = cities_df.to_dicts()

    # Process in batches
    batch_size = config.CITY_BATCH_SIZE
    total_processed = 0

    for i in tqdm(range(0, len(cities), batch_size), desc="Batches"):
        batch = cities[i : i + batch_size]
        processed = process_city_batch(
            batch, geometries, population_grid, output_dir, progress
        )
        total_processed += processed

    # Mark completion
    sentinel = output_dir / ".complete"
    sentinel.touch()

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    progress.print_summary()
    print(f"Total cities processed: {total_processed}")


if __name__ == "__main__":
    main()

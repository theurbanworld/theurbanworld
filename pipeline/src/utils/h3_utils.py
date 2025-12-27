"""
H3 hexagon utilities.

Purpose: Common H3 operations used across multiple scripts
Decision log:
  - Use h3 library (v4+) for core operations
  - h3ronpy for efficient raster-to-H3 conversion
  - Resolution 9 for maps (~0.1 km²), resolution 10 for profiles (~0.015 km²)
Date: 2025-12-08 (updated 2025-12-26)
"""

import math
from typing import Iterable

import h3
import numpy as np

from .geometry_utils import haversine_distance_km


def h3_to_parent(h3_index: int | str, parent_res: int) -> str:
    """Get parent cell at coarser resolution."""
    if isinstance(h3_index, int):
        h3_index = h3.int_to_str(h3_index)
    return h3.cell_to_parent(h3_index, parent_res)


def h3_to_children(h3_index: int | str, child_res: int) -> list[str]:
    """Get child cells at finer resolution."""
    if isinstance(h3_index, int):
        h3_index = h3.int_to_str(h3_index)
    return list(h3.cell_to_children(h3_index, child_res))


def h3_cell_area_km2(h3_index: int | str) -> float:
    """Get area of H3 cell in square kilometers."""
    if isinstance(h3_index, int):
        h3_index = h3.int_to_str(h3_index)
    return h3.cell_area(h3_index, unit="km^2")


def h3_cell_to_latlng(h3_index: int | str) -> tuple[float, float]:
    """Get cell center as (lat, lng)."""
    if isinstance(h3_index, int):
        h3_index = h3.int_to_str(h3_index)
    return h3.cell_to_latlng(h3_index)


def latlng_to_h3(lat: float, lng: float, resolution: int) -> str:
    """Convert lat/lng to H3 cell."""
    return h3.latlng_to_cell(lat, lng, resolution)


def h3_distance_km(h3_index1: int | str, h3_index2: int | str) -> float:
    """Calculate distance between H3 cell centroids in km."""
    lat1, lon1 = h3_cell_to_latlng(h3_index1)
    lat2, lon2 = h3_cell_to_latlng(h3_index2)
    return haversine_distance_km(lat1, lon1, lat2, lon2)


def cells_within_radius(
    lat: float,
    lng: float,
    radius_km: float,
    resolution: int,
) -> set[str]:
    """
    Get all H3 cells within radius of point.

    Uses k-ring expansion and distance filtering for accuracy.
    """
    center = h3.latlng_to_cell(lat, lng, resolution)

    # Estimate k-ring size needed
    avg_edge_km = h3.average_hexagon_edge_length(resolution, unit="km")
    k = int(math.ceil(radius_km / avg_edge_km)) + 2  # Buffer for safety

    # Get k-ring
    candidates = h3.grid_disk(center, k)

    # Filter by actual distance
    result = set()
    for cell in candidates:
        cell_lat, cell_lng = h3.cell_to_latlng(cell)
        if haversine_distance_km(lat, lng, cell_lat, cell_lng) <= radius_km:
            result.add(cell)

    return result


def polygon_to_h3_cells(polygon, resolution: int) -> set[str]:
    """
    Convert shapely polygon to H3 cells.

    Args:
        polygon: Shapely Polygon in WGS84
        resolution: H3 resolution

    Returns:
        Set of H3 cell IDs
    """
    # Convert to GeoJSON format for h3
    coords = list(polygon.exterior.coords)
    # GeoJSON is [lng, lat]
    geojson = {"type": "Polygon", "coordinates": [[[lon, lat] for lat, lon in coords]]}

    try:
        cells = h3.polygon_to_cells(geojson, resolution)
        return set(cells)
    except Exception:
        # Fallback: sample points within polygon
        return _polygon_to_h3_sampling(polygon, resolution)


def _polygon_to_h3_sampling(polygon, resolution: int, samples_per_km2: int = 100) -> set[str]:
    """Fallback polygon conversion using point sampling."""
    from shapely.ops import unary_union

    minx, miny, maxx, maxy = polygon.bounds
    area_deg2 = (maxx - minx) * (maxy - miny)
    # Rough conversion to km²
    area_km2 = area_deg2 * 111 * 111 * math.cos(math.radians((miny + maxy) / 2))

    num_samples = int(max(100, area_km2 * samples_per_km2))

    cells = set()
    for _ in range(num_samples):
        # Random point in bounding box
        x = minx + (maxx - minx) * np.random.random()
        y = miny + (maxy - miny) * np.random.random()

        from shapely import Point

        if polygon.contains(Point(x, y)):
            cell = h3.latlng_to_cell(y, x, resolution)
            cells.add(cell)

    return cells


def get_h3_neighbors(h3_index: int | str) -> set[str]:
    """Get the 6 neighboring H3 cells."""
    if isinstance(h3_index, int):
        h3_index = h3.int_to_str(h3_index)
    return set(h3.grid_ring(h3_index, 1))


def h3_cells_to_multipolygon(cells: Iterable[str]):
    """
    Convert set of H3 cells to a MultiPolygon geometry.

    Returns:
        Shapely MultiPolygon
    """
    from shapely import MultiPolygon, Polygon

    polygons = []
    for cell in cells:
        boundary = h3.cell_to_boundary(cell)
        # boundary is [(lat, lng), ...] - convert to [(lng, lat), ...]
        coords = [(lng, lat) for lat, lng in boundary]
        coords.append(coords[0])  # Close the polygon
        polygons.append(Polygon(coords))

    return MultiPolygon(polygons)


def compute_population_weighted_centroid(
    cells: Iterable[str],
    population: dict[str, float],
) -> tuple[float, float]:
    """
    Compute population-weighted centroid for a set of H3 cells.

    Uses 3D Cartesian averaging for spherical accuracy.

    Args:
        cells: H3 cell IDs
        population: Map of cell ID to population

    Returns:
        (latitude, longitude) of weighted centroid
    """
    total_pop = 0.0
    x_sum = y_sum = z_sum = 0.0

    for cell in cells:
        pop = population.get(cell, 0)
        if pop <= 0:
            continue

        lat, lng = h3_cell_to_latlng(cell)
        lat_rad = math.radians(lat)
        lng_rad = math.radians(lng)

        # Convert to 3D Cartesian
        x = math.cos(lat_rad) * math.cos(lng_rad)
        y = math.cos(lat_rad) * math.sin(lng_rad)
        z = math.sin(lat_rad)

        # Weight by population
        x_sum += x * pop
        y_sum += y * pop
        z_sum += z * pop
        total_pop += pop

    if total_pop == 0:
        # Fall back to geometric centroid
        return _compute_geometric_centroid(cells)

    # Average and convert back to lat/lng
    x_avg = x_sum / total_pop
    y_avg = y_sum / total_pop
    z_avg = z_sum / total_pop

    lng_center = math.degrees(math.atan2(y_avg, x_avg))
    hyp = math.sqrt(x_avg**2 + y_avg**2)
    lat_center = math.degrees(math.atan2(z_avg, hyp))

    return lat_center, lng_center


def _compute_geometric_centroid(cells: Iterable[str]) -> tuple[float, float]:
    """Compute simple geometric centroid of H3 cells."""
    lats = []
    lngs = []
    for cell in cells:
        lat, lng = h3_cell_to_latlng(cell)
        lats.append(lat)
        lngs.append(lng)

    if not lats:
        return 0.0, 0.0

    return sum(lats) / len(lats), sum(lngs) / len(lngs)


def assign_cells_to_rings(
    cells: Iterable[str],
    center_lat: float,
    center_lng: float,
    ring_width_km: float = 1.0,
    max_radius_km: float = 50.0,
) -> dict[int, list[str]]:
    """
    Assign H3 cells to concentric rings based on distance from center.

    Ring 0 = 0-1km, Ring 1 = 1-2km, etc.

    Args:
        cells: H3 cell IDs
        center_lat, center_lng: Center point coordinates
        ring_width_km: Width of each ring in km
        max_radius_km: Maximum distance to consider

    Returns:
        Dict mapping ring index to list of cells
    """
    num_rings = int(max_radius_km / ring_width_km)
    rings: dict[int, list[str]] = {i: [] for i in range(num_rings)}

    for cell in cells:
        cell_lat, cell_lng = h3_cell_to_latlng(cell)
        distance_km = haversine_distance_km(center_lat, center_lng, cell_lat, cell_lng)

        ring_idx = int(distance_km / ring_width_km)
        if 0 <= ring_idx < num_rings:
            rings[ring_idx].append(cell)

    return rings

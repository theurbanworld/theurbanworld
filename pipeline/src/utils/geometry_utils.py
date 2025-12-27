"""
Geometry and projection utilities.

Purpose: Handle coordinate transformations and geometry operations
Decision log:
  - GHSL data is in Mollweide (EPSG:54009), need to convert to WGS84 for H3
  - Use pyproj for accurate coordinate transformations
  - Shapely for geometry operations
Date: 2025-12-08
"""

import math

import pyproj
import shapely
from shapely import Point, Polygon
from shapely.ops import transform as shapely_transform

# Standard CRS definitions
WGS84 = pyproj.CRS("EPSG:4326")
MOLLWEIDE = pyproj.CRS("ESRI:54009")  # World Mollweide


def create_transformer(from_crs: pyproj.CRS, to_crs: pyproj.CRS) -> pyproj.Transformer:
    """Create pyproj transformer for coordinate conversion."""
    return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True)


def reproject_geometry(
    geometry: shapely.Geometry,
    from_crs: pyproj.CRS,
    to_crs: pyproj.CRS,
) -> shapely.Geometry:
    """Reproject a shapely geometry between coordinate systems."""
    transformer = create_transformer(from_crs, to_crs)
    return shapely_transform(transformer.transform, geometry)


def mollweide_to_wgs84(geometry: shapely.Geometry) -> shapely.Geometry:
    """Convert geometry from Mollweide to WGS84."""
    return reproject_geometry(geometry, MOLLWEIDE, WGS84)


def wgs84_to_mollweide(geometry: shapely.Geometry) -> shapely.Geometry:
    """Convert geometry from WGS84 to Mollweide."""
    return reproject_geometry(geometry, WGS84, MOLLWEIDE)


def fix_invalid_geometry(geometry: shapely.Geometry) -> shapely.Geometry:
    """Fix invalid geometry using buffer(0) trick."""
    if not geometry.is_valid:
        return geometry.buffer(0)
    return geometry


def get_bounding_box(geometry: shapely.Geometry) -> tuple[float, float, float, float]:
    """Get bounding box as (minx, miny, maxx, maxy)."""
    return geometry.bounds


def compute_centroid(geometry: shapely.Geometry) -> tuple[float, float]:
    """Get centroid as (lat, lon) for WGS84 geometry."""
    centroid = geometry.centroid
    return (centroid.y, centroid.x)  # (lat, lon)


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance between two points in kilometers.

    Uses the haversine formula for accuracy.
    """
    R = 6371.0  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def create_circle_polygon(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    num_points: int = 64,
) -> Polygon:
    """
    Create a circular polygon approximation in WGS84.

    Useful for clipping operations.
    """
    points = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        # Approximate degree offset for radius
        # 1 degree latitude ~= 111km
        # 1 degree longitude ~= 111km * cos(lat)
        lat_offset = (radius_km / 111.0) * math.cos(angle)
        lon_offset = (radius_km / (111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle)
        points.append((center_lon + lon_offset, center_lat + lat_offset))

    points.append(points[0])  # Close the polygon
    return Polygon(points)


def buffer_bbox(
    bbox: tuple[float, float, float, float],
    buffer_km: float,
) -> tuple[float, float, float, float]:
    """
    Add buffer to bounding box.

    Args:
        bbox: (minx, miny, maxx, maxy) in degrees
        buffer_km: Buffer distance in kilometers

    Returns:
        Expanded bounding box
    """
    minx, miny, maxx, maxy = bbox
    # Approximate degree offset
    lat_buffer = buffer_km / 111.0
    lon_buffer = buffer_km / (111.0 * math.cos(math.radians((miny + maxy) / 2)))

    return (
        minx - lon_buffer,
        miny - lat_buffer,
        maxx + lon_buffer,
        maxy + lat_buffer,
    )

"""
GHSL tile management utilities.

Purpose: Handle GHSL tile grid operations and URL construction
Decision log:
  - GHSL uses a Mollweide-based tile grid
  - Each tile is ~10000x10000 pixels at 100m resolution
  - Tile IDs are R{row}_C{col} format
Date: 2025-12-08
"""

from pathlib import Path
from typing import NamedTuple

import shapely
from shapely import box


class TileInfo(NamedTuple):
    """Information about a GHSL tile."""

    row: int
    col: int
    tile_id: str


def parse_tile_id(tile_id: str) -> tuple[int, int]:
    """
    Parse tile ID string to row/column.

    Args:
        tile_id: Format "R5_C19"

    Returns:
        Tuple of (row, col)
    """
    parts = tile_id.split("_")
    row = int(parts[0][1:])
    col = int(parts[1][1:])
    return row, col


def format_tile_id(row: int, col: int) -> str:
    """
    Format row/column to tile ID string.

    Args:
        row: Tile row number
        col: Tile column number

    Returns:
        Tile ID string like "R5_C19"
    """
    return f"R{row}_C{col}"


def get_tile_from_filename(filename: str) -> TileInfo | None:
    """
    Extract tile info from GHSL filename.

    Args:
        filename: Like "GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R5_C19.tif"

    Returns:
        TileInfo or None if not a tile file
    """
    # Look for R{n}_C{n} pattern
    import re

    match = re.search(r"R(\d+)_C(\d+)", filename)
    if match:
        row = int(match.group(1))
        col = int(match.group(2))
        return TileInfo(row=row, col=col, tile_id=format_tile_id(row, col))
    return None


def find_tiles_in_directory(directory: Path) -> list[TileInfo]:
    """
    Find all GHSL tiles in a directory.

    Args:
        directory: Path to search

    Returns:
        List of TileInfo for found tiles
    """
    tiles = []
    for tif_file in directory.glob("*.tif"):
        tile_info = get_tile_from_filename(tif_file.name)
        if tile_info:
            tiles.append(tile_info)
    return sorted(tiles, key=lambda t: (t.row, t.col))


def get_tile_path(directory: Path, row: int, col: int) -> Path | None:
    """
    Find the tile file for given row/col in directory.

    Returns:
        Path to tile file or None if not found
    """
    pattern = f"*R{row}_C{col}*.tif"
    matches = list(directory.glob(pattern))
    return matches[0] if matches else None


# Approximate Mollweide tile boundaries
# These are rough estimates - actual boundaries depend on GHSL grid definition
TILE_SIZE_MOLLWEIDE = 1000000  # ~1000km per tile in Mollweide meters


def estimate_tiles_for_bbox_wgs84(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
) -> list[tuple[int, int]]:
    """
    Estimate which GHSL tiles cover a WGS84 bounding box.

    This is approximate - for accurate results, use the GHSL tile schema.

    Args:
        minx, miny, maxx, maxy: WGS84 bounding box

    Returns:
        List of (row, col) tuples
    """
    # Convert to approximate Mollweide coordinates
    # Mollweide x: -18040000 to +18040000
    # Mollweide y: -9020000 to +9020000

    # Rough conversion (accurate near equator)
    def wgs84_to_mollweide_approx(lon: float, lat: float) -> tuple[float, float]:
        import math

        # Very rough approximation
        x = lon * 111320 * math.cos(math.radians(lat))
        y = lat * 110540
        return x, y

    # Get corners in Mollweide
    x1, y1 = wgs84_to_mollweide_approx(minx, miny)
    x2, y2 = wgs84_to_mollweide_approx(maxx, maxy)

    # Convert to tile indices
    # GHSL grid starts at some offset - these are rough estimates
    # Tile 0,0 is approximately at the northwest corner

    # Approximate grid: rows 0-17, cols 0-35
    col1 = max(0, min(35, int((x1 + 18040000) / TILE_SIZE_MOLLWEIDE)))
    col2 = max(0, min(35, int((x2 + 18040000) / TILE_SIZE_MOLLWEIDE)))
    row1 = max(0, min(17, int((9020000 - y2) / TILE_SIZE_MOLLWEIDE)))
    row2 = max(0, min(17, int((9020000 - y1) / TILE_SIZE_MOLLWEIDE)))

    tiles = []
    for row in range(row1, row2 + 1):
        for col in range(col1, col2 + 1):
            tiles.append((row, col))

    return tiles

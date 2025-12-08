"""
Raster processing utilities.

Purpose: Handle raster loading, reprojection, and chunked processing
Decision log:
  - Use rioxarray for Dask-integrated raster loading
  - Chunk size of 2048x2048 balances memory vs overhead
  - Reproject to WGS84 before H3 conversion (h3ronpy requirement)
  - Nodata handling critical for population rasters
Date: 2024-12-08
"""

from pathlib import Path
from typing import Generator

import numpy as np
import rasterio
import rioxarray
import xarray as xr


def open_raster(
    path: Path,
    chunks: tuple[int, int] | None = (2048, 2048),
) -> xr.DataArray:
    """
    Open raster with optional Dask chunking.

    Args:
        path: Path to raster file
        chunks: Chunk size as (y, x) or None for no chunking

    Returns:
        xarray DataArray with optional Dask backing
    """
    if chunks:
        data = rioxarray.open_rasterio(
            path,
            chunks={"x": chunks[1], "y": chunks[0]},
            lock=False,  # Allow parallel reads
        )
    else:
        data = rioxarray.open_rasterio(path)

    # Squeeze out single band dimension if present
    if "band" in data.dims and data.sizes["band"] == 1:
        data = data.squeeze("band", drop=True)

    return data


def get_raster_info(path: Path) -> dict:
    """
    Get basic information about a raster file.

    Returns:
        Dict with crs, bounds, shape, dtype, nodata
    """
    with rasterio.open(path) as src:
        return {
            "crs": src.crs,
            "bounds": src.bounds,
            "shape": (src.height, src.width),
            "dtype": src.dtypes[0],
            "nodata": src.nodata,
            "transform": src.transform,
            "count": src.count,
        }


def reproject_to_wgs84(
    data: xr.DataArray,
    resolution: float | None = None,
    nodata: float = -200.0,
) -> xr.DataArray:
    """
    Reproject raster to EPSG:4326 (WGS84).

    Required for h3ronpy which only accepts WGS84 input.

    Args:
        data: Input raster in any CRS
        resolution: Output resolution in degrees (None for auto)
        nodata: Nodata value to use

    Returns:
        Reprojected DataArray
    """
    return data.rio.reproject(
        "EPSG:4326",
        resolution=resolution,
        resampling=rasterio.enums.Resampling.bilinear,
        nodata=nodata,
    )


def iter_windows(
    data: xr.DataArray,
    window_size: tuple[int, int] = (1024, 1024),
) -> Generator[tuple[dict, xr.DataArray], None, None]:
    """
    Iterate over raster in spatial windows.

    Yields (slice_dict, data_window) tuples.

    Args:
        data: Input DataArray
        window_size: Window size as (height, width)

    Yields:
        Tuple of (slice indices, window DataArray)
    """
    height = data.sizes.get("y", data.sizes.get("latitude", 0))
    width = data.sizes.get("x", data.sizes.get("longitude", 0))

    y_dim = "y" if "y" in data.dims else "latitude"
    x_dim = "x" if "x" in data.dims else "longitude"

    for y_start in range(0, height, window_size[0]):
        for x_start in range(0, width, window_size[1]):
            y_end = min(y_start + window_size[0], height)
            x_end = min(x_start + window_size[1], width)

            slices = {
                y_dim: slice(y_start, y_end),
                x_dim: slice(x_start, x_end),
            }

            window = data.isel(**slices)
            yield slices, window


def mask_nodata(data: xr.DataArray, nodata: float = -200.0) -> xr.DataArray:
    """
    Mask nodata values in raster.

    Args:
        data: Input DataArray
        nodata: Value to treat as nodata

    Returns:
        DataArray with nodata masked as NaN
    """
    return data.where(data != nodata)


def clip_to_bbox(
    data: xr.DataArray,
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
) -> xr.DataArray:
    """
    Clip raster to bounding box.

    Args:
        data: Input DataArray
        minx, miny, maxx, maxy: Bounding box coordinates

    Returns:
        Clipped DataArray
    """
    from shapely import box

    bbox = box(minx, miny, maxx, maxy)
    return data.rio.clip([bbox], crs="EPSG:4326")


def get_transform(data: xr.DataArray):
    """Get affine transform from DataArray."""
    return data.rio.transform()


def get_resolution(data: xr.DataArray) -> tuple[float, float]:
    """Get resolution as (y_res, x_res) from DataArray."""
    transform = data.rio.transform()
    return abs(transform.e), abs(transform.a)


def sample_at_points(
    data: xr.DataArray,
    points: list[tuple[float, float]],
) -> list[float]:
    """
    Sample raster values at point locations.

    Args:
        data: Input DataArray
        points: List of (lat, lon) coordinates

    Returns:
        List of sampled values
    """
    values = []
    for lat, lon in points:
        try:
            val = float(data.sel(x=lon, y=lat, method="nearest").values)
            values.append(val)
        except Exception:
            values.append(np.nan)
    return values


def compute_statistics(data: xr.DataArray, nodata: float = -200.0) -> dict:
    """
    Compute basic statistics for raster.

    Args:
        data: Input DataArray
        nodata: Nodata value to exclude

    Returns:
        Dict with min, max, mean, std, count
    """
    valid = data.where(data != nodata)

    return {
        "min": float(valid.min().values),
        "max": float(valid.max().values),
        "mean": float(valid.mean().values),
        "std": float(valid.std().values),
        "count": int((data != nodata).sum().values),
    }

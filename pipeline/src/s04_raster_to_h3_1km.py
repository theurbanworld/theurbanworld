"""
04 - Convert 1km GHSL-POP rasters to H3 for time series.

Purpose: Transform 1km population rasters (1975-2020) to H3 grid
Input: data/raw/ghsl_pop_1km/*.tif (1km global files, all epochs)
Output:
  - data/interim/h3_pop_1km/{year}.parquet (per-epoch)
  - data/interim/h3_pop_1km/time_series.parquet (wide format)

Decision log:
  - 1km data is 100x smaller than 100m - can process globally
  - Use same H3 resolution 9 as 100m for consistency
  - Create wide-format time series for efficient city lookups
  - DuckDB pivot for efficient wide transformation
Date: 2024-12-08
"""

import gc
import multiprocessing
import warnings
from pathlib import Path

# Fix multiprocessing semaphore leak on macOS
if multiprocessing.get_start_method(allow_none=True) is None:
    multiprocessing.set_start_method("spawn")
warnings.filterwarnings("ignore", message=".*leaked semaphore.*")

import click
import duckdb
import polars as pl
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_raw_path
from .utils.progress import ProgressTracker
from .utils.raster_utils import get_raster_info, open_raster, reproject_to_wgs84


def raster_to_h3(
    data_array,
    resolution: int = 9,
    nodata: float = -200.0,
    max_tile_size: int = 8000,
) -> pl.DataFrame:
    """Convert raster to H3 using h3ronpy, with chunking for large rasters."""
    from affine import Affine
    from h3ronpy.raster import raster_to_dataframe
    import numpy as np

    values = data_array.values
    if hasattr(values, "compute"):
        values = values.compute()

    height, width = values.shape
    transform = data_array.rio.transform()

    # Small rasters: process directly
    if height <= max_tile_size and width <= max_tile_size:
        table = raster_to_dataframe(
            values,
            transform,
            resolution,
            nodata_value=nodata,
            compact=False,
        )
        return pl.from_arrow(table).rename({"cell": "h3_index", "value": "population"})

    # Large rasters: process in tiles
    print(f"    Processing in tiles ({height}x{width} > {max_tile_size}x{max_tile_size})...")
    results = []
    tile_count = 0

    for row_start in range(0, height, max_tile_size):
        for col_start in range(0, width, max_tile_size):
            row_end = min(row_start + max_tile_size, height)
            col_end = min(col_start + max_tile_size, width)

            # Extract tile
            tile = values[row_start:row_end, col_start:col_end]

            # Skip if all nodata/invalid
            valid = (tile != nodata) & ~np.isnan(tile) & (tile > 0)
            if not np.any(valid):
                continue

            # Calculate tile transform (shift origin to tile corner)
            tile_transform = transform * Affine.translation(col_start, row_start)

            # Convert tile to H3
            table = raster_to_dataframe(
                tile,
                tile_transform,
                resolution,
                nodata_value=nodata,
                compact=False,
            )

            if len(table) > 0:
                results.append(pl.from_arrow(table))
                tile_count += 1

            del tile
            gc.collect()

    print(f"    Processed {tile_count} tiles with data")

    if not results:
        return pl.DataFrame({"h3_index": [], "population": []})

    # Combine and aggregate overlapping cells at tile boundaries
    combined = pl.concat(results)
    return combined.group_by("cell").agg(
        pl.col("value").sum()
    ).rename({"cell": "h3_index", "value": "population"})


def process_epoch(
    epoch: int,
    input_dir: Path,
    output_dir: Path,
    h3_resolution: int = 9,
) -> Path | None:
    """
    Process a single epoch's global 1km file.

    Args:
        epoch: Year (1975, 1980, ..., 2020)
        input_dir: Directory with input GeoTIFFs
        output_dir: Directory for output parquet
        h3_resolution: Target H3 resolution

    Returns:
        Path to output parquet or None if failed
    """
    # Find the file for this epoch
    pattern = f"*E{epoch}*1000*.tif"
    matches = list(input_dir.glob(pattern))

    if not matches:
        print(f"  No file found for epoch {epoch}")
        return None

    input_path = matches[0]
    output_path = output_dir / f"{epoch}.parquet"

    # Get raster info
    info = get_raster_info(input_path)
    nodata = info["nodata"] if info["nodata"] is not None else -200.0

    print(f"  Processing {input_path.name}...")
    print(f"    Shape: {info['shape']}, CRS: {info['crs']}")

    # Load and reproject (1km data is small enough to process at once)
    data = open_raster(input_path, chunks=None)
    print("    Reprojecting to WGS84...")
    data_wgs84 = reproject_to_wgs84(data, nodata=nodata)

    # Convert to H3
    print(f"    Converting to H3 res {h3_resolution}...")
    df = raster_to_h3(data_wgs84, h3_resolution, nodata)

    # Filter
    df = df.filter(pl.col("population") > 0)
    print(f"    Generated {len(df):,} H3 cells")

    # Save
    df.write_parquet(output_path)

    # Cleanup
    del data, data_wgs84, df
    gc.collect()

    return output_path


def build_time_series(
    epoch_dir: Path,
    output_path: Path,
    epochs: list[int],
) -> None:
    """
    Build wide-format time series from per-epoch parquet files.

    Args:
        epoch_dir: Directory with epoch parquet files
        output_path: Path for output parquet
        epochs: List of epochs to include
    """
    print("\nBuilding time series table...")

    conn = duckdb.connect()

    # Load all epochs and pivot to wide format
    # First, union all epochs with year column
    union_parts = []
    for epoch in epochs:
        epoch_file = epoch_dir / f"{epoch}.parquet"
        if epoch_file.exists():
            union_parts.append(
                f"SELECT h3_index, population, {epoch} as year FROM read_parquet('{epoch_file}')"
            )

    if not union_parts:
        print("  No epoch files found!")
        return

    union_query = " UNION ALL ".join(union_parts)

    # Pivot to wide format
    pivot_cols = ", ".join([f"pop_{epoch}" for epoch in epochs])
    sum_cols = ", ".join(
        [f"SUM(CASE WHEN year = {epoch} THEN population ELSE 0 END) as pop_{epoch}" for epoch in epochs]
    )

    query = f"""
        SELECT
            h3_index,
            {sum_cols}
        FROM ({union_query})
        GROUP BY h3_index
    """

    print("  Executing pivot query...")
    result = conn.execute(query).pl()

    print(f"  Created time series for {len(result):,} H3 cells")

    # Save
    result.write_parquet(output_path)
    print(f"  Saved to {output_path}")

    conn.close()


@click.command()
@click.option("--test-only", is_flag=True, help="Process only recent epochs")
def main(test_only: bool = False):
    """Convert 1km GHSL-POP rasters to H3 time series."""
    print("=" * 60)
    print("1km Raster to H3 Time Series Conversion")
    print("=" * 60)

    input_dir = get_raw_path("ghsl_pop_1km")
    output_dir = get_interim_path("h3_pop_1km")

    # Select epochs
    if test_only:
        epochs = [2000, 2010, 2020]  # Subset for testing
    else:
        epochs = config.GHSL_POP_EPOCHS

    print(f"Processing {len(epochs)} epochs: {epochs}")

    # Initialize progress
    progress_file = output_dir / "_progress.json"
    progress = ProgressTracker(progress_file)
    progress.initialize([str(e) for e in epochs])

    # Process each epoch
    print("\nProcessing epochs...")
    for epoch in tqdm(epochs, desc="Epochs"):
        epoch_str = str(epoch)

        if progress.is_complete(epoch_str):
            print(f"  {epoch} already processed, skipping...")
            continue

        progress.mark_in_progress(epoch_str)

        try:
            output_path = process_epoch(
                epoch,
                input_dir,
                output_dir,
                h3_resolution=config.H3_RESOLUTION_1KM,
            )

            if output_path:
                progress.mark_complete(epoch_str, {"output": str(output_path)})
            else:
                progress.mark_failed(epoch_str, "No input file found")

        except Exception as e:
            progress.mark_failed(epoch_str, str(e))
            print(f"\n  ERROR on {epoch}: {e}")

    # Build time series
    time_series_path = output_dir / "time_series.parquet"
    build_time_series(output_dir, time_series_path, epochs)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    progress.print_summary()


if __name__ == "__main__":
    main()

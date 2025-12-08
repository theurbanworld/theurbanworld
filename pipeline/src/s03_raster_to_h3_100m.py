"""
03 - Convert 100m GHSL-POP raster to H3 hexagons.

Purpose: Transform 100m population raster (2020) to H3 resolution 9 grid
Input:
  - data/raw/ghsl_pop_100m/*.tif (100m Mollweide tiles)
  - data/interim/urban_centers.parquet (for tile filtering)
Output:
  - data/interim/h3_pop_100m/{tile_id}.parquet (per-tile)
  - data/processed/h3_tiles/h3_pop_2020_res9.parquet (merged)

Decision log:
  - Reproject to WGS84 before H3 conversion (h3ronpy requirement)
  - Process one tile at a time to stay within 16GB RAM
  - Use h3ronpy for efficient raster-to-H3 conversion
  - Merge tiles with DuckDB for efficient deduplication
  - Handle tile boundary overlaps by summing population
Date: 2024-12-08
"""

import gc
from pathlib import Path

import click
import duckdb
import numpy as np
import polars as pl
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_processed_path, get_raw_path
from .utils.progress import ProgressTracker
from .utils.raster_utils import get_raster_info, mask_nodata, open_raster, reproject_to_wgs84
from .utils.tile_utils import find_tiles_in_directory, get_tile_path


def raster_to_h3_simple(
    data_array,
    resolution: int = 9,
    nodata: float = -200.0,
    min_value: float = 0.0,
) -> pl.DataFrame:
    """
    Convert raster to H3 cells using point sampling.

    This is a fallback method when h3ronpy is not available or fails.
    Less accurate but memory-efficient.

    Args:
        data_array: xarray DataArray in WGS84
        resolution: H3 resolution
        nodata: Nodata value to skip
        min_value: Minimum value to include

    Returns:
        Polars DataFrame with h3_index and population columns
    """
    import h3

    # Get coordinate arrays
    y_coords = data_array.coords["y"].values
    x_coords = data_array.coords["x"].values

    # Get data as numpy array
    values = data_array.values
    if hasattr(values, "compute"):
        values = values.compute()

    # Build H3 index
    h3_data: dict[str, float] = {}

    # Sample every pixel
    for i, lat in enumerate(y_coords):
        for j, lon in enumerate(x_coords):
            val = values[i, j]
            if val == nodata or val < min_value or np.isnan(val):
                continue

            cell = h3.latlng_to_cell(float(lat), float(lon), resolution)
            h3_data[cell] = h3_data.get(cell, 0.0) + float(val)

    if not h3_data:
        return pl.DataFrame({"h3_index": [], "population": []})

    return pl.DataFrame(
        {"h3_index": list(h3_data.keys()), "population": list(h3_data.values())}
    )


def raster_to_h3_h3ronpy(
    data_array,
    resolution: int = 9,
    nodata: float = -200.0,
) -> pl.DataFrame:
    """
    Convert raster to H3 cells using h3ronpy (fast, multi-threaded).

    Args:
        data_array: xarray DataArray in WGS84
        resolution: H3 resolution
        nodata: Nodata value

    Returns:
        Polars DataFrame with h3_index and population columns
    """
    try:
        from h3ronpy.raster import raster_to_dataframe

        # Get values and transform
        values = data_array.values
        if hasattr(values, "compute"):
            values = values.compute()

        transform = data_array.rio.transform()

        # Convert using h3ronpy
        df = raster_to_dataframe(
            values,
            transform,
            resolution,
            nodata_value=nodata,
            compact=False,
        )

        # Convert to polars
        return pl.from_pandas(df).rename({"value": "population"})

    except ImportError:
        print("  h3ronpy not available, using fallback method...")
        return raster_to_h3_simple(data_array, resolution, nodata)
    except Exception as e:
        print(f"  h3ronpy failed ({e}), using fallback method...")
        return raster_to_h3_simple(data_array, resolution, nodata)


def process_tile(
    tile_path: Path,
    output_dir: Path,
    h3_resolution: int = 9,
    chunk_size: tuple[int, int] = (2048, 2048),
) -> Path | None:
    """
    Process a single GHSL tile to H3.

    Args:
        tile_path: Path to input GeoTIFF
        output_dir: Directory for output parquet
        h3_resolution: Target H3 resolution
        chunk_size: Chunk size for processing

    Returns:
        Path to output parquet or None if failed
    """
    tile_id = tile_path.stem.split("_")[-2] + "_" + tile_path.stem.split("_")[-1]
    output_path = output_dir / f"{tile_id}.parquet"

    # Get raster info
    info = get_raster_info(tile_path)
    nodata = info["nodata"] if info["nodata"] is not None else -200.0

    print(f"  Loading {tile_path.name}...")
    print(f"    Shape: {info['shape']}, CRS: {info['crs']}")

    # Load raster with chunking
    data = open_raster(tile_path, chunks=chunk_size)

    # Reproject to WGS84
    print("    Reprojecting to WGS84...")
    data_wgs84 = reproject_to_wgs84(data, nodata=nodata)

    # Convert to H3
    print(f"    Converting to H3 res {h3_resolution}...")
    df = raster_to_h3_h3ronpy(data_wgs84, h3_resolution, nodata)

    # Filter out zero/negative populations
    df = df.filter(pl.col("population") > 0)

    print(f"    Generated {len(df):,} H3 cells")

    # Save
    df.write_parquet(output_path)

    # Cleanup
    del data, data_wgs84, df
    gc.collect()

    return output_path


def merge_tiles_duckdb(
    tile_dir: Path,
    output_path: Path,
) -> None:
    """
    Merge per-tile parquet files using DuckDB.

    Handles deduplication of H3 cells at tile boundaries by summing population.

    Args:
        tile_dir: Directory containing tile parquet files
        output_path: Path for merged output
    """
    print("\nMerging tiles with DuckDB...")

    conn = duckdb.connect()

    # Count input files
    parquet_files = list(tile_dir.glob("*.parquet"))
    print(f"  Found {len(parquet_files)} tile files")

    if not parquet_files:
        print("  No tiles to merge!")
        return

    # Create merged table with deduplication
    # H3 cells at tile boundaries may appear in multiple tiles
    query = f"""
        SELECT
            h3_index,
            SUM(population) as population
        FROM read_parquet('{tile_dir}/*.parquet')
        GROUP BY h3_index
        ORDER BY population DESC
    """

    print("  Executing merge query...")
    result = conn.execute(query).pl()

    print(f"  Merged to {len(result):,} unique H3 cells")
    print(f"  Total population: {result['population'].sum():,.0f}")

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.write_parquet(output_path)
    print(f"  Saved to {output_path}")

    conn.close()


@click.command()
@click.option("--test-only", is_flag=True, help="Process only test city tiles")
def main(test_only: bool = False):
    """Convert 100m GHSL-POP raster to H3."""
    print("=" * 60)
    print("100m Raster to H3 Conversion")
    print("=" * 60)

    # Find tiles
    tile_dir = get_raw_path("ghsl_pop_100m")
    tiles = find_tiles_in_directory(tile_dir)

    if not tiles:
        print("ERROR: No tiles found. Run download first.")
        return

    print(f"Found {len(tiles)} tiles")

    # Initialize progress tracker
    output_dir = get_interim_path("h3_pop_100m")
    progress_file = output_dir / "_progress.json"
    progress = ProgressTracker(progress_file)

    tile_ids = [t.tile_id for t in tiles]
    progress.initialize(tile_ids)

    # Process each tile
    print("\nProcessing tiles...")
    for tile_info in tqdm(tiles, desc="Tiles"):
        tile_id = tile_info.tile_id

        if progress.is_complete(tile_id):
            continue

        progress.mark_in_progress(tile_id)

        tile_path = get_tile_path(tile_dir, tile_info.row, tile_info.col)
        if not tile_path:
            progress.mark_failed(tile_id, "Tile file not found")
            continue

        try:
            output_path = process_tile(
                tile_path,
                output_dir,
                h3_resolution=config.H3_RESOLUTION_MAP,
                chunk_size=config.RASTER_CHUNK_SIZE,
            )

            if output_path:
                progress.mark_complete(tile_id, {"output": str(output_path)})
            else:
                progress.mark_failed(tile_id, "Processing returned None")

        except MemoryError as e:
            print(f"\n  Memory error on {tile_id}, trying smaller chunks...")
            try:
                output_path = process_tile(
                    tile_path,
                    output_dir,
                    h3_resolution=config.H3_RESOLUTION_MAP,
                    chunk_size=(1024, 1024),
                )
                if output_path:
                    progress.mark_complete(tile_id, {"output": str(output_path)})
                else:
                    progress.mark_failed(tile_id, str(e))
            except Exception as e2:
                progress.mark_failed(tile_id, str(e2))

        except Exception as e:
            progress.mark_failed(tile_id, str(e))
            print(f"\n  ERROR on {tile_id}: {e}")

    # Merge all tiles
    final_output = get_processed_path("h3_tiles") / "h3_pop_2020_res9.parquet"
    merge_tiles_duckdb(output_dir, final_output)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    progress.print_summary()


if __name__ == "__main__":
    main()

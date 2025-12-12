"""
03 - Convert 100m GHSL-POP rasters to H3 (Modal cloud version).

Purpose: Process all 100m tiles in parallel on Modal for faster execution
Usage:
  modal run src/s03_raster_to_h3_100m_modal.py  # Process all global tiles
  modal run src/s03_raster_to_h3_100m_modal.py --cities-only  # Only tiles for cities
  modal run src/s03_raster_to_h3_100m_modal.py --skip-existing  # Resume
  modal run src/s03_raster_to_h3_100m_modal.py --merge-only  # Just merge existing tiles
  modal run src/s03_raster_to_h3_100m_modal.py --download-local  # Download to local disk

Setup (one-time):
  1. Create R2 bucket in Cloudflare dashboard
  2. Create R2 API token with read/write permissions
  3. Create Modal secret:
     modal secret create r2-credentials \\
       R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com \\
       R2_ACCESS_KEY_ID=<your_access_key> \\
       R2_SECRET_ACCESS_KEY=<your_secret_key> \\
       R2_BUCKET_NAME=<your_bucket_name>

Cost estimate: ~$2-4 for global (375 tiles), ~$1-2 for cities-only (203 tiles)
Time estimate: ~5-10 minutes wall-clock with parallel processing

Decision log:
  - Process tiles in parallel (up to 100 containers)
  - 8GB memory per container (sufficient for 100m tiles)
  - Download data directly in container (faster than mounting)
  - Results saved to Modal volume, then uploaded to R2
  - DuckDB merge handles tile boundary deduplication
  - Uses GHSL tile grid shapefile (375 tiles) to know which tiles exist
Date: 2024-12-12
"""

import modal

# Modal app setup
app = modal.App("ghsl-h3-100m-conversion")

# Container image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgdal-dev", "gdal-bin")
    .pip_install(
        "pyarrow>=15.0.0",
        "h3ronpy>=0.22.0",
        "polars>=1.0.0",
        "rioxarray>=0.15.0",
        "xarray>=2024.1.0",
        "rasterio>=1.3.0",
        "pyproj>=3.6.0",
        "httpx>=0.27.0",
        "tqdm>=4.66.0",
        "duckdb>=1.0.0",
        "affine>=2.4.0",
        "numpy>=1.26.0",
        "boto3>=1.35.0",
    )
)

# Volume for persisting results
volume = modal.Volume.from_name("ghsl-h3-100m-results", create_if_missing=True)

# Constants
GHSL_URL_TEMPLATE = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_54009_100/V1-0/tiles/"
    "GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R{row}_C{col}.zip"
)
H3_RESOLUTION = 9  # Res 9 (~0.1 km²) for 100m input data

# 375 valid tiles from GHSL tile grid shapefile (land-only, excludes ocean tiles)
# Extracted from GHSL2_0_MWD_L1_tile_schema_land.shp
# fmt: off
VALID_TILES = [
    (1, 13), (1, 14), (1, 15), (1, 16), (1, 17), (1, 18), (1, 19), (1, 20), (1, 21), (1, 22),
    (1, 23), (1, 24), (1, 25), (2, 8), (2, 9), (2, 10), (2, 11), (2, 12), (2, 13), (2, 14),
    (2, 15), (2, 16), (2, 17), (2, 18), (2, 19), (2, 20), (2, 21), (2, 22), (2, 23), (2, 24),
    (2, 25), (2, 26), (2, 27), (2, 28), (2, 29), (2, 30), (3, 5), (3, 6), (3, 7), (3, 8),
    (3, 9), (3, 10), (3, 11), (3, 12), (3, 13), (3, 14), (3, 15), (3, 16), (3, 18), (3, 19),
    (3, 20), (3, 21), (3, 22), (3, 23), (3, 24), (3, 25), (3, 26), (3, 27), (3, 28), (3, 29),
    (3, 30), (3, 31), (3, 32), (4, 8), (4, 9), (4, 10), (4, 11), (4, 12), (4, 13), (4, 14),
    (4, 18), (4, 19), (4, 20), (4, 21), (4, 22), (4, 23), (4, 24), (4, 25), (4, 26), (4, 27),
    (4, 28), (4, 29), (4, 30), (4, 31), (5, 8), (5, 9), (5, 10), (5, 11), (5, 12), (5, 13),
    (5, 16), (5, 17), (5, 18), (5, 19), (5, 20), (5, 21), (5, 22), (5, 23), (5, 24), (5, 25),
    (5, 26), (5, 27), (5, 28), (5, 29), (5, 30), (5, 31), (6, 2), (6, 3), (6, 8), (6, 9),
    (6, 10), (6, 11), (6, 13), (6, 17), (6, 18), (6, 19), (6, 20), (6, 21), (6, 22), (6, 23),
    (6, 24), (6, 25), (6, 26), (6, 27), (6, 28), (6, 29), (6, 30), (6, 31), (6, 32), (7, 2),
    (7, 3), (7, 4), (7, 7), (7, 8), (7, 9), (7, 10), (7, 11), (7, 12), (7, 13), (7, 16),
    (7, 17), (7, 18), (7, 19), (7, 20), (7, 21), (7, 22), (7, 23), (7, 24), (7, 25), (7, 26),
    (7, 27), (7, 28), (7, 29), (7, 30), (7, 31), (7, 32), (7, 33), (7, 35), (8, 8), (8, 9),
    (8, 10), (8, 11), (8, 12), (8, 13), (8, 16), (8, 17), (8, 18), (8, 19), (8, 20), (8, 21),
    (8, 22), (8, 23), (8, 24), (8, 26), (8, 27), (8, 28), (8, 29), (8, 30), (8, 31), (8, 32),
    (8, 33), (8, 34), (8, 35), (8, 36), (9, 1), (9, 2), (9, 3), (9, 9), (9, 10), (9, 11),
    (9, 12), (9, 13), (9, 14), (9, 16), (9, 17), (9, 18), (9, 19), (9, 20), (9, 21), (9, 22),
    (9, 23), (9, 24), (9, 26), (9, 27), (9, 28), (9, 29), (9, 30), (9, 31), (9, 32), (9, 33),
    (9, 34), (9, 35), (9, 36), (10, 1), (10, 3), (10, 5), (10, 9), (10, 10), (10, 11), (10, 12),
    (10, 13), (10, 14), (10, 15), (10, 17), (10, 19), (10, 20), (10, 21), (10, 22), (10, 23), (10, 24),
    (10, 26), (10, 28), (10, 29), (10, 30), (10, 31), (10, 32), (10, 33), (10, 34), (10, 35), (10, 36),
    (11, 1), (11, 2), (11, 3), (11, 4), (11, 5), (11, 11), (11, 12), (11, 13), (11, 14), (11, 15),
    (11, 18), (11, 20), (11, 21), (11, 22), (11, 23), (11, 24), (11, 28), (11, 29), (11, 30), (11, 31),
    (11, 32), (11, 33), (11, 34), (11, 35), (11, 36), (12, 1), (12, 2), (12, 3), (12, 4), (12, 5),
    (12, 6), (12, 11), (12, 12), (12, 13), (12, 14), (12, 15), (12, 16), (12, 20), (12, 21), (12, 22),
    (12, 23), (12, 24), (12, 25), (12, 29), (12, 30), (12, 31), (12, 32), (12, 33), (12, 34), (12, 35),
    (12, 36), (13, 2), (13, 5), (13, 6), (13, 7), (13, 8), (13, 9), (13, 11), (13, 12), (13, 13),
    (13, 14), (13, 20), (13, 21), (13, 22), (13, 23), (13, 29), (13, 30), (13, 31), (13, 32), (13, 33),
    (13, 34), (14, 11), (14, 12), (14, 13), (14, 14), (14, 17), (14, 18), (14, 20), (14, 21), (14, 25),
    (14, 29), (14, 30), (14, 31), (14, 32), (14, 33), (14, 34), (15, 4), (15, 12), (15, 13), (15, 14),
    (15, 22), (15, 23), (15, 24), (15, 31), (15, 32), (15, 33), (16, 13), (16, 14), (16, 15), (16, 16),
    (16, 17), (16, 19), (16, 24), (16, 30), (16, 31), (17, 9), (17, 14), (17, 15), (17, 16), (17, 18),
    (17, 19), (17, 20), (17, 21), (17, 22), (17, 23), (17, 24), (17, 25), (17, 26), (17, 27), (17, 28),
    (18, 12), (18, 13), (18, 14), (18, 15), (18, 16), (18, 17), (18, 18), (18, 19), (18, 20), (18, 21),
    (18, 22), (18, 23), (18, 24), (18, 25), (18, 26),
]
# fmt: on


@app.function(
    image=image,
    memory=8192,  # 8GB - sufficient for 100m tiles
    cpu=2.0,  # 2 CPUs for h3ronpy multi-threading
    timeout=600,  # 10 minutes max per tile
    retries=2,
    volumes={"/results": volume},
)
def process_tile(row: int, col: int) -> dict:
    """Process a single tile and save to volume."""
    import gc
    import io
    import tempfile
    import zipfile
    from pathlib import Path

    import httpx
    import numpy as np
    import polars as pl
    import rioxarray  # noqa: F401 - needed for rio accessor
    import xarray as xr
    from h3ronpy.raster import raster_to_dataframe

    tile_id = f"R{row}_C{col}"
    print(f"[{tile_id}] Starting processing...")

    # Download the file
    url = GHSL_URL_TEMPLATE.format(row=row, col=col)
    print(f"[{tile_id}] Downloading from {url}")

    with httpx.Client(timeout=300) as client:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        zip_bytes = response.content

    print(f"[{tile_id}] Downloaded {len(zip_bytes) / 1e6:.1f} MB")

    # Extract tif from zip
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            tif_names = [n for n in zf.namelist() if n.endswith(".tif")]
            if not tif_names:
                return {"tile_id": tile_id, "status": "error", "reason": "no_tif_in_zip"}

            tif_name = tif_names[0]
            zf.extract(tif_name, tmppath)
            tif_path = tmppath / tif_name

        print(f"[{tile_id}] Extracted {tif_name}")

        # Load raster
        data = xr.open_dataarray(tif_path, engine="rasterio")
        nodata = data.rio.nodata or -200.0

        print(f"[{tile_id}] Loaded raster: shape={data.shape}, crs={data.rio.crs}")

        # Reproject to WGS84
        print(f"[{tile_id}] Reprojecting to WGS84...")
        data_wgs84 = data.rio.reproject("EPSG:4326", nodata=nodata)

        # Get values - squeeze to 2D and ensure contiguous float32
        values = data_wgs84.values
        if values.ndim == 3:
            values = values.squeeze()  # Remove band dimension (1, H, W) -> (H, W)
        values = np.ascontiguousarray(values, dtype=np.float32)

        transform = data_wgs84.rio.transform()

        # Free memory
        del data, zip_bytes, data_wgs84
        gc.collect()

        print(f"[{tile_id}] Converting to H3 res {H3_RESOLUTION}... (shape: {values.shape})")

        # Convert to H3
        table = raster_to_dataframe(
            values,
            transform,
            H3_RESOLUTION,
            nodata_value=float(nodata),
            compact=False,
        )

        # Convert to polars
        df = pl.from_arrow(table).rename({"cell": "h3_index", "value": "population"})

        # Filter out zero/negative populations
        df = df.filter(pl.col("population") > 0)

        print(f"[{tile_id}] Generated {len(df):,} H3 cells")

        if len(df) == 0:
            print(f"[{tile_id}] No populated cells, skipping save")
            return {"tile_id": tile_id, "status": "skipped", "reason": "no_population", "cells": 0}

        # Save to volume
        results_dir = Path("/results/tiles")
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = results_dir / f"{tile_id}.parquet"
        df.write_parquet(output_path)
        volume.commit()

        file_size = output_path.stat().st_size / 1e6
        print(f"[{tile_id}] Complete! Saved {output_path.name} ({file_size:.1f} MB, {len(df):,} cells)")

        return {
            "tile_id": tile_id,
            "status": "success",
            "cells": len(df),
            "file_size_mb": round(file_size, 2),
        }


@app.function(
    image=image,
    memory=16384,  # 16GB for merge operation
    volumes={"/results": volume},
    timeout=1200,  # 20 minutes for merge
)
def merge_all_tiles() -> str:
    """Merge all tile parquet files using DuckDB."""
    import duckdb
    from pathlib import Path

    print("Merging tiles with DuckDB...")

    results_dir = Path("/results/tiles")
    output_dir = Path("/results")

    # Find all tile parquet files
    parquet_files = sorted(results_dir.glob("R*_C*.parquet"))
    print(f"  Found {len(parquet_files)} tile files")

    if not parquet_files:
        return "No tiles to merge!"

    # Create merged table with deduplication
    # H3 cells at tile boundaries may appear in multiple tiles
    conn = duckdb.connect()

    query = f"""
        SELECT
            h3_index,
            SUM(population) as population
        FROM read_parquet('{results_dir}/R*_C*.parquet')
        GROUP BY h3_index
        ORDER BY population DESC
    """

    print("  Executing merge query...")
    result = conn.execute(query).pl()

    print(f"  Merged to {len(result):,} unique H3 cells")
    print(f"  Total population: {result['population'].sum():,.0f}")

    # Save merged result
    merged_path = output_dir / "h3_pop_2025_res9.parquet"
    result.write_parquet(merged_path)

    # Commit volume
    volume.commit()

    conn.close()

    file_size = merged_path.stat().st_size / 1e6
    return f"Saved h3_pop_2025_res9.parquet ({file_size:.1f} MB, {len(result):,} cells)"


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=60,
)
def list_existing_tiles() -> list[str]:
    """List tiles already processed in volume."""
    from pathlib import Path

    results_dir = Path("/results/tiles")
    if not results_dir.exists():
        return []

    existing = []
    for f in results_dir.glob("R*_C*.parquet"):
        existing.append(f.stem)
    return sorted(existing)


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=600,
)
def download_results() -> dict[str, bytes]:
    """Download results from volume (for local storage)."""
    from pathlib import Path

    results_dir = Path("/results")
    files = {}

    # Get merged file
    merged_path = results_dir / "h3_pop_2025_res9.parquet"
    if merged_path.exists():
        files[merged_path.name] = merged_path.read_bytes()
        print(f"  Read {merged_path.name}: {len(files[merged_path.name]) / 1e6:.1f} MB")

    return files


@app.function(
    image=image,
    volumes={"/results": volume},
    secrets=[modal.Secret.from_name("r2-credentials")],
    timeout=600,
)
def upload_to_r2(prefix: str = "ghsl-pop-100m") -> list[str]:
    """Upload results from volume to R2."""
    import os
    from pathlib import Path

    import boto3

    # Get R2 credentials from environment
    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["R2_BUCKET_NAME"]

    print(f"Uploading to R2 bucket: {bucket_name}")

    # Create S3 client for R2
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    results_dir = Path("/results")
    uploaded = []

    # Upload merged file
    merged_path = results_dir / "h3_pop_2025_res9.parquet"
    if merged_path.exists():
        key = f"{prefix}/{merged_path.name}"
        file_size = merged_path.stat().st_size / 1e6

        print(f"  Uploading {merged_path.name} ({file_size:.1f} MB) -> {key}")
        s3.upload_file(str(merged_path), bucket_name, key)
        uploaded.append(key)

    print(f"Uploaded {len(uploaded)} files to s3://{bucket_name}/{prefix}/")
    return uploaded


def get_all_tile_coords() -> list[tuple[int, int]]:
    """Get all valid tile coordinates (375 tiles with land coverage)."""
    return list(VALID_TILES)


def get_city_tile_coords() -> list[tuple[int, int]]:
    """Get tile coordinates needed for cities in cities.parquet.

    Filters to only tiles that actually exist (from VALID_TILES).
    Some small island cities reference tiles that don't exist.
    """
    import polars as pl
    from pathlib import Path

    cities_path = Path("data/interim/cities.parquet")
    if not cities_path.exists():
        print("Warning: cities.parquet not found, using all tiles")
        return list(VALID_TILES)

    df = pl.read_parquet(cities_path)

    # Extract unique tiles from required_tiles column
    city_tiles = set()
    for tile_list in df["required_tiles"].to_list():
        if tile_list:
            for tile_id in tile_list:
                # Parse "R5_C18" format
                parts = tile_id.split("_")
                row = int(parts[0][1:])  # Remove 'R' prefix
                col = int(parts[1][1:])  # Remove 'C' prefix
                city_tiles.add((row, col))

    # Filter to only tiles that exist
    valid_tiles = set(VALID_TILES)
    existing_city_tiles = city_tiles & valid_tiles

    if len(existing_city_tiles) < len(city_tiles):
        missing = len(city_tiles) - len(existing_city_tiles)
        print(f"  Note: {missing} city tiles don't exist (small islands), skipping them")

    return sorted(existing_city_tiles)


@app.local_entrypoint()
def main(
    cities_only: bool = False,
    skip_existing: bool = False,
    merge_only: bool = False,
    upload_only: bool = False,
    download_local: bool = False,
    test: bool = False,
):
    """Run the 100m H3 conversion pipeline.

    Args:
        cities_only: Only process tiles needed for cities (203 vs 375 global)
        skip_existing: Skip tiles already in volume (for resuming)
        merge_only: Only merge existing tile files
        upload_only: Only upload existing results to R2
        download_local: Download results to local disk instead of R2
        test: Process single tile for testing
    """
    import time
    from pathlib import Path

    print("=" * 60)
    print("100m Raster to H3 (Modal Cloud)")
    print("=" * 60)

    start_time = time.time()

    # Upload-only mode
    if upload_only:
        print("\nUpload-only mode: uploading existing files to R2...")
        uploaded = upload_to_r2.remote()
        print(f"  Uploaded {len(uploaded)} files")
        total_time = time.time() - start_time
        print(f"\nComplete! Total time: {total_time:.1f}s")
        return

    # Merge-only mode
    if merge_only:
        print("\nMerge-only mode: merging existing tile files...")
        summary = merge_all_tiles.remote()
        print(f"  {summary}")

        if download_local:
            _download_to_local(Path("data/processed/h3_tiles"))
        else:
            print("\nUploading to R2...")
            uploaded = upload_to_r2.remote()
            print(f"  Uploaded {len(uploaded)} files")

        total_time = time.time() - start_time
        print(f"\nComplete! Total time: {total_time:.1f}s")
        return

    # Determine which tiles to process
    if test:
        tiles_to_process = [(5, 18)]  # Paris tile for testing
        print("\nTest mode: processing only R5_C18")
    elif cities_only:
        tiles_to_process = get_city_tile_coords()
        print(f"\nCities-only mode: {len(tiles_to_process)} tiles for all cities")
    else:
        tiles_to_process = get_all_tile_coords()
        print(f"\nGlobal mode: {len(tiles_to_process)} tiles (from shapefile)")

    # Check for existing tiles in volume
    if skip_existing:
        existing = list_existing_tiles.remote()
        if existing:
            print(f"  Found {len(existing)} existing tiles in volume")
            existing_set = set(existing)
            tiles_to_process = [
                (r, c) for r, c in tiles_to_process if f"R{r}_C{c}" not in existing_set
            ]
            if not tiles_to_process:
                print("  All tiles already processed! Use --merge-only to create merged file.")
                return
            print(f"  Will process {len(tiles_to_process)} remaining tiles")

    # Process tiles in parallel
    print(f"\nProcessing {len(tiles_to_process)} tiles...")

    futures = []
    for row, col in tiles_to_process:
        futures.append(process_tile.spawn(row, col))

    # Collect results
    results = {"success": 0, "skipped": 0, "error": 0, "total_cells": 0}
    for (row, col), future in zip(tiles_to_process, futures):
        tile_id = f"R{row}_C{col}"
        try:
            result = future.get()
            status = result.get("status", "unknown")
            results[status] = results.get(status, 0) + 1
            if status == "success":
                results["total_cells"] += result.get("cells", 0)
            print(f"  {tile_id}: {status} ({result.get('cells', 0):,} cells)")
        except Exception as e:
            results["error"] += 1
            print(f"  {tile_id}: error - {e}")

    print(f"\nProcessed tiles: {results['success']} success, {results['skipped']} skipped, {results['error']} errors")
    print(f"Total H3 cells: {results['total_cells']:,}")

    # Merge all tiles
    if results["success"] > 0:
        print("\nMerging all tiles...")
        summary = merge_all_tiles.remote()
        print(f"  {summary}")

        # Upload to R2 or download locally
        if download_local:
            _download_to_local(Path("data/processed/h3_tiles"))
        else:
            print("\nUploading to R2...")
            uploaded = upload_to_r2.remote()
            print(f"  Uploaded {len(uploaded)} files")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Complete! Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print("=" * 60)


def _download_to_local(output_dir) -> None:
    """Helper to download results to local disk."""
    from pathlib import Path

    output_dir = Path(output_dir)
    print("\nDownloading results to local disk...")
    files = download_results.remote()

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        output_path = output_dir / filename
        output_path.write_bytes(content)
        print(f"  Saved {output_path}")

    print(f"Results saved to {output_dir}")

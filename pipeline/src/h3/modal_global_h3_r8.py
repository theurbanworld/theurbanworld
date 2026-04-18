"""
Convert global GHSL-POP 1km rasters to H3 resolution 8 using tiled exactextract.

Purpose: Process the entire world's population data into H3 cells, not just
         city-bounded areas. This enables proto-city analysis (pre-birth population),
         post-city tracking (death year), and buffer zone heatmaps.

Strategy: Tile the globe into 10°×10° cells, generate H3-R8 polygons per tile,
          and run exactextract for accurate area-weighted population assignment.

Usage:
  modal run src/h3/modal_global_h3_r8.py                    # Full pipeline
  modal run src/h3/modal_global_h3_r8.py --skip-existing     # Resume
  modal run src/h3/modal_global_h3_r8.py --merge-only        # Merge + timeseries only
  modal run src/h3/modal_global_h3_r8.py --upload-only       # Upload to R2 only
  modal run src/h3/modal_global_h3_r8.py --download-local    # Download locally

Architecture:
  Phase A: Download 12 epoch rasters to Modal volume (parallel, ~10 min)
  Phase B: Process ~200 land tiles × 12 epochs (parallel, ~30-45 min)
  Phase C: Merge tile results per epoch + build timeseries (~5 min)
  Phase D: Upload to R2

Cost estimate: ~$10-20 on Modal
Time estimate: ~45-60 minutes wall-clock

Date: 2026-03-30
"""

import modal

app = modal.App("ghsl-global-h3")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgdal-dev", "gdal-bin")
    .pip_install(
        "exactextract>=0.2.0",
        "geopandas>=1.0.0",
        "h3>=4.0.0",
        "pyarrow>=15.0.0",
        "polars>=1.0.0",
        "rasterio>=1.3.0",
        "httpx>=0.27.0",
        "duckdb>=1.0.0",
        "numpy>=1.26.0",
        "boto3>=1.35.0",
        "shapely>=2.0.0",
    )
)

volume = modal.Volume.from_name("ghsl-global-h3-results", create_if_missing=True)

GHSL_URL_TEMPLATE = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_POP_GLOBE_R2023A/GHS_POP_E{epoch}_GLOBE_R2023A_4326_30ss/V1-0/"
    "GHS_POP_E{epoch}_GLOBE_R2023A_4326_30ss_V1_0.zip"
)
EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
H3_RESOLUTION = 8
TILE_SIZE_DEG = 10


def generate_tile_list() -> list[tuple[int, int]]:
    """Generate (lat_start, lon_start) for all 10°×10° tiles covering the globe."""
    tiles = []
    for lat in range(-90, 90, TILE_SIZE_DEG):
        for lon in range(-180, 180, TILE_SIZE_DEG):
            tiles.append((lat, lon))
    return tiles


# ─── Phase A: Download rasters to volume ─────────────────────────────────────


@app.function(
    image=image,
    memory=2048,  # 2GB — just downloading + unzipping
    cpu=0.25,
    timeout=1800,  # 30 min for large downloads
    retries=2,
    volumes={"/results": volume},
)
def download_raster(epoch: int) -> str:
    """Download and extract one epoch's WGS84 raster to the volume."""
    import io
    import shutil
    import tempfile
    import zipfile
    from pathlib import Path

    import httpx

    raster_dir = Path("/results/rasters")
    raster_dir.mkdir(parents=True, exist_ok=True)

    output_path = raster_dir / f"GHS_POP_E{epoch}_4326_30ss.tif"
    if output_path.exists():
        print(f"[{epoch}] Already downloaded: {output_path.name}")
        return f"Epoch {epoch}: already exists"

    url = GHSL_URL_TEMPLATE.format(epoch=epoch)
    print(f"[{epoch}] Downloading {url}")

    with httpx.Client(timeout=600) as client:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        zip_bytes = response.content

    print(f"[{epoch}] Downloaded {len(zip_bytes) / 1e6:.1f} MB")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        tif_names = [n for n in zf.namelist() if n.endswith(".tif")]
        if not tif_names:
            raise ValueError(f"No .tif file found in archive for {epoch}")

        # Extract to temp, then copy to volume (can't rename across filesystems)
        with tempfile.TemporaryDirectory() as tmpdir:
            zf.extract(tif_names[0], tmpdir)
            src = Path(tmpdir) / tif_names[0]
            shutil.copy2(str(src), str(output_path))

    volume.commit()
    file_size = output_path.stat().st_size / 1e6
    print(f"[{epoch}] Saved {output_path.name} ({file_size:.1f} MB)")
    return f"Epoch {epoch}: {file_size:.1f} MB"


# ─── Phase B: Process tiles ──────────────────────────────────────────────────


@app.function(
    image=image,
    memory=8192,  # 8GB — pre-filtered cells keep memory low
    cpu=1.0,
    timeout=7200,  # 2h max (processes all 12 epochs)
    retries=1,
    volumes={"/results": volume},
)
def process_tile(lat_start: int, lon_start: int) -> str:
    """
    Process one 10°×10° tile across all epochs.

    Optimization: instead of generating ALL H3 cells for the tile (1-2M),
    we scan each raster window to find non-zero pixels, map them to H3 cells,
    and only build polygons for cells that actually have population. For sparse
    tiles this is 100-1000x fewer polygons. A 1-ring buffer ensures
    exactextract gets accurate area-weighted values at cell boundaries.
    """
    from pathlib import Path

    import geopandas as gpd
    import numpy as np
    import polars as pl
    import rasterio
    from exactextract import exact_extract
    from rasterio.windows import from_bounds
    from shapely import Polygon

    import h3

    lat_end = lat_start + TILE_SIZE_DEG
    lon_end = lon_start + TILE_SIZE_DEG
    tile_id = f"{lat_start:+03d}_{lon_start:+04d}"

    tiles_dir = Path("/results/tiles")
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Check if already fully processed
    existing = list(tiles_dir.glob(f"tile_{tile_id}_*.parquet"))
    if len(existing) >= len(EPOCHS):
        print(f"[{tile_id}] Already processed all epochs")
        return f"Tile {tile_id}: already complete"

    raster_dir = Path("/results/rasters")

    # Clamp latitude to avoid h3 issues at poles
    clamped_lat_start = max(lat_start, -85)
    clamped_lat_end = min(lat_end, 85)
    if clamped_lat_start >= clamped_lat_end:
        return f"Tile {tile_id}: polar region, skipping"

    # ── Scan ALL epoch rasters to find populated H3 cells ──
    # Union of cells across all epochs ensures one GeoDataFrame works for all
    all_populated_cells: set[str] = set()

    for epoch in EPOCHS:
        raster_path = raster_dir / f"GHS_POP_E{epoch}_4326_30ss.tif"
        if not raster_path.exists():
            continue

        with rasterio.open(raster_path) as src:
            try:
                window = from_bounds(lon_start, lat_start, lon_end, lat_end, src.transform)
                data = src.read(1, window=window)
                transform = src.window_transform(window)
            except Exception:
                continue

            if np.nanmax(data) <= 0:
                continue

            # Find non-zero pixel coordinates and map to H3 cells
            rows, cols = np.where(data > 0)
            for r, c in zip(rows, cols):
                # Pixel center in geographic coordinates
                px_lng = transform.c + (c + 0.5) * transform.a
                px_lat = transform.f + (r + 0.5) * transform.e
                cell = h3.latlng_to_cell(px_lat, px_lng, H3_RESOLUTION)
                all_populated_cells.add(cell)

    if not all_populated_cells:
        print(f"[{tile_id}] No populated cells across any epoch, skipping")
        return f"Tile {tile_id}: no population (skipped)"

    # Add 1-ring neighbors for accurate area-weighted extraction at boundaries
    buffered_cells: set[str] = set()
    for cell in all_populated_cells:
        buffered_cells.add(cell)
        buffered_cells.update(h3.grid_ring(cell, 1))

    print(
        f"[{tile_id}] {len(all_populated_cells):,} populated cells + {len(buffered_cells) - len(all_populated_cells):,} buffer = {len(buffered_cells):,} total"
    )

    # ── Build polygon GeoDataFrame (only for populated + buffer cells) ──
    h3_data = []
    for cell in buffered_cells:
        boundary = h3.cell_to_boundary(cell)
        coords = [(lng, lat) for lat, lng in boundary]
        coords.append(coords[0])
        h3_data.append({"h3_index": cell, "geometry": Polygon(coords)})

    cells_gdf = gpd.GeoDataFrame(h3_data, crs="EPSG:4326")
    print(f"[{tile_id}] GeoDataFrame ready: {len(cells_gdf):,} cells")

    # ── Process each epoch ──
    total_cells_with_pop = 0
    for epoch in EPOCHS:
        output_path = tiles_dir / f"tile_{tile_id}_{epoch}.parquet"
        if output_path.exists():
            print(f"[{tile_id}][{epoch}] Already exists, skipping")
            continue

        raster_path = raster_dir / f"GHS_POP_E{epoch}_4326_30ss.tif"
        if not raster_path.exists():
            print(f"[{tile_id}][{epoch}] Raster not found, skipping")
            continue

        print(f"[{tile_id}][{epoch}] Running exactextract...")
        results_df = exact_extract(
            str(raster_path),
            cells_gdf,
            ops=["sum"],
            include_cols=["h3_index"],
            output="pandas",
        )

        df = pl.from_pandas(results_df).rename({"sum": "population"})

        # Convert h3_index string to int64 for compact storage
        df = df.with_columns(pl.col("h3_index").map_elements(h3.str_to_int, return_dtype=pl.Int64))

        # Keep only cells with population > 0
        df = df.filter(pl.col("population") > 0)

        df.write_parquet(output_path)
        total_cells_with_pop += len(df)
        print(f"[{tile_id}][{epoch}] {len(df):,} cells with population")

    volume.commit()
    return f"Tile {tile_id}: {len(buffered_cells):,} cells, {total_cells_with_pop:,} populated (across all epochs)"


# ─── Phase C: Merge tiles + build timeseries ─────────────────────────────────


@app.function(
    image=image,
    memory=16384,  # 16GB for merging large datasets via DuckDB
    cpu=2.0,
    timeout=3600,
    volumes={"/results": volume},
)
def merge_and_build_timeseries() -> str:
    """Merge per-tile results into per-epoch files, then build timeseries."""
    from pathlib import Path

    import duckdb

    tiles_dir = Path("/results/tiles")
    results_dir = Path("/results")

    # ── Merge tiles per epoch ──
    for epoch in EPOCHS:
        output_path = results_dir / f"global_h3_r8_pop_{epoch}.parquet"

        tile_files = sorted(tiles_dir.glob(f"tile_*_{epoch}.parquet"))
        if not tile_files:
            print(f"[{epoch}] No tile files found")
            continue

        print(f"[{epoch}] Merging {len(tile_files)} tile files...")

        # Use DuckDB for efficient merge (handles dedup if needed)
        conn = duckdb.connect()
        file_list = ", ".join(f"'{f}'" for f in tile_files)
        query = f"""
            SELECT h3_index, SUM(population) as population
            FROM read_parquet([{file_list}])
            GROUP BY h3_index
        """
        df = conn.execute(query).pl()
        conn.close()

        df.write_parquet(output_path)
        print(f"[{epoch}] Merged: {len(df):,} cells -> {output_path.name}")

    # ── Build timeseries ──
    print("\nBuilding global timeseries...")
    conn = duckdb.connect()

    epoch_files = sorted(results_dir.glob("global_h3_r8_pop_[0-9][0-9][0-9][0-9].parquet"))
    epochs = [int(f.stem.split("_")[-1]) for f in epoch_files]

    if not epochs:
        return "No epoch files found"

    union_parts = []
    for epoch in epochs:
        f = results_dir / f"global_h3_r8_pop_{epoch}.parquet"
        union_parts.append(f"SELECT h3_index, population, {epoch} as year FROM read_parquet('{f}')")

    union_query = " UNION ALL ".join(union_parts)
    sum_cols = ", ".join(
        f"SUM(CASE WHEN year = {e} THEN population ELSE 0 END) as pop_{e}" for e in epochs
    )

    query = f"""
        SELECT h3_index, {sum_cols}
        FROM ({union_query})
        GROUP BY h3_index
    """

    print("  Executing pivot query...")
    result = conn.execute(query).pl()
    conn.close()

    ts_path = results_dir / "global_h3_r8_pop_timeseries.parquet"
    result.write_parquet(ts_path)

    volume.commit()
    file_size = ts_path.stat().st_size / 1e6
    print(f"  Saved timeseries: {len(result):,} cells ({file_size:.1f} MB)")

    return f"Merged {len(epochs)} epochs, timeseries: {len(result):,} cells ({file_size:.1f} MB)"


# ─── Upload to R2 ────────────────────────────────────────────────────────────


@app.function(
    image=image,
    volumes={"/results": volume},
    secrets=[modal.Secret.from_name("r2-credentials")],
    timeout=3600,  # 1h — uploading ~14 GB
)
def upload_to_r2(prefix: str = "ghsl-global-h3-r8") -> list[str]:
    """Upload merged epoch files and timeseries to R2 (parallel)."""
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    from threading import Lock

    import boto3

    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["R2_BUCKET_NAME"]

    def make_client():
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    results_dir = Path("/results")
    upload_tasks = []
    for path in sorted(results_dir.glob("global_h3_r8_pop_*.parquet")):
        upload_tasks.append((path, f"{prefix}/{path.name}"))

    print(f"Uploading {len(upload_tasks)} files with 8 threads...")

    uploaded: list[str] = []
    Lock()

    def upload_one(item: tuple) -> str:
        path, key = item
        file_size = path.stat().st_size / 1e6
        print(f"  Uploading {path.name} ({file_size:.1f} MB) -> {key}")
        client = make_client()
        client.upload_file(str(path), bucket_name, key)
        return key

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(upload_one, task) for task in upload_tasks]
        for future in as_completed(futures):
            uploaded.append(future.result())

    print(f"Uploaded {len(uploaded)} files to s3://{bucket_name}/{prefix}/")
    return uploaded


# ─── Utility functions ────────────────────────────────────────────────────────


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=60,
)
def list_volume_status() -> str:
    """List what's on the volume for debugging."""
    from pathlib import Path

    results_dir = Path("/results")
    lines = []

    # Rasters
    rasters = sorted(results_dir.glob("rasters/*.tif"))
    lines.append(f"Rasters: {len(rasters)}")
    for r in rasters:
        lines.append(f"  {r.name}: {r.stat().st_size / 1e6:.1f} MB")

    # Tiles
    tile_files = sorted(results_dir.glob("tiles/tile_*.parquet"))
    lines.append(f"\nTile files: {len(tile_files)}")
    if tile_files:
        # Count by epoch
        epoch_counts = {}
        for f in tile_files:
            epoch = int(f.stem.split("_")[-1])
            epoch_counts[epoch] = epoch_counts.get(epoch, 0) + 1
        for epoch, count in sorted(epoch_counts.items()):
            lines.append(f"  {epoch}: {count} tiles")

    # Merged files
    merged = sorted(results_dir.glob("global_h3_r8_pop_*.parquet"))
    lines.append(f"\nMerged files: {len(merged)}")
    for m in merged:
        lines.append(f"  {m.name}: {m.stat().st_size / 1e6:.1f} MB")

    return "\n".join(lines)


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=600,
)
def download_results() -> dict[str, bytes]:
    """Download merged results from volume (for local storage)."""
    from pathlib import Path

    results_dir = Path("/results")
    files = {}
    for path in results_dir.glob("global_h3_r8_pop_*.parquet"):
        files[path.name] = path.read_bytes()
        print(f"  Read {path.name}: {len(files[path.name]) / 1e6:.1f} MB")
    return files


# ─── Entrypoint ───────────────────────────────────────────────────────────────


@app.local_entrypoint()
def main(
    skip_existing: bool = False,
    merge_only: bool = False,
    upload_only: bool = False,
    download_local: bool = False,
    status: bool = False,
    dry_run: bool = False,
):
    """Run the global H3 rasterization pipeline.

    Args:
        skip_existing: Skip tiles/rasters already on volume
        merge_only: Only merge tiles + build timeseries (skip processing)
        upload_only: Only upload existing results to R2
        download_local: Download results locally instead of uploading to R2
        status: Print volume status and exit
        dry_run: Download 1 raster (2020) and process 1 tile (0°,30° — East Africa)
    """
    import time

    print("=" * 60)
    print("Global GHSL-POP → H3 R8 (tiled exactextract)")
    print("=" * 60)

    start_time = time.time()

    if status:
        print(list_volume_status.remote())
        return

    if upload_only:
        uploaded = upload_to_r2.remote()
        print(f"Uploaded {len(uploaded)} files")
        return

    if merge_only:
        summary = merge_and_build_timeseries.remote()
        print(summary)
        if download_local:
            _download_to_local()
        else:
            uploaded = upload_to_r2.remote()
            print(f"Uploaded {len(uploaded)} files")
        return

    if dry_run:
        print("\n*** DRY RUN: 1 raster (2020) + 1 tile (0°, 30° — East Africa) ***\n")

        # Download just the 2020 raster
        print("--- Downloading 2020 raster ---")
        result = download_raster.remote(2020)
        print(f"  {result}")

        # Process one tile
        print("\n--- Processing tile (0, 30) ---")
        result = process_tile.remote(0, 30)
        print(f"  {result}")

        # Check what landed on the volume
        print("\n--- Volume status ---")
        print(list_volume_status.remote())

        total_time = time.time() - start_time
        print(f"\nDry run complete in {total_time:.1f}s")
        return

    # ── Phase A: Download rasters ──
    print("\n--- Phase A: Download rasters ---")
    print(f"Downloading {len(EPOCHS)} epoch rasters in parallel...")

    futures_dl = [download_raster.spawn(epoch) for epoch in EPOCHS]
    for epoch, future in zip(EPOCHS, futures_dl):
        result = future.get()
        print(f"  {result}")

    dl_time = time.time() - start_time
    print(f"Downloads complete in {dl_time:.1f}s")

    # ── Phase B: Process tiles ──
    print("\n--- Phase B: Process tiles ---")
    tiles = generate_tile_list()
    print(f"Processing {len(tiles)} tiles in parallel...")

    futures_tiles = [process_tile.spawn(lat, lon) for lat, lon in tiles]

    populated_count = 0
    skipped_count = 0
    for (lat, lon), future in zip(tiles, futures_tiles):
        result = future.get()
        if "skipped" in result or "0 H3 cells" in result or "polar" in result:
            skipped_count += 1
        else:
            populated_count += 1
            print(f"  {result}")

    tile_time = time.time() - start_time - dl_time
    print(
        f"\nProcessed {populated_count} populated tiles, skipped {skipped_count} ({tile_time:.1f}s)"
    )

    # ── Phase C: Merge + timeseries ──
    print("\n--- Phase C: Merge + build timeseries ---")
    summary = merge_and_build_timeseries.remote()
    print(f"  {summary}")

    # ── Phase D: Upload/download ──
    if download_local:
        _download_to_local()
    else:
        print("\n--- Phase D: Upload to R2 ---")
        uploaded = upload_to_r2.remote()
        print(f"  Uploaded {len(uploaded)} files")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Complete! Total time: {total_time:.1f}s ({total_time / 60:.1f} min)")
    print("=" * 60)


def _download_to_local():
    """Helper to download results to local disk."""
    from pathlib import Path

    output_dir = Path("data/processed/global_h3_r8")
    print(f"\nDownloading results to {output_dir}...")
    files = download_results.remote()

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        path = output_dir / filename
        path.write_bytes(content)
        print(f"  Saved {path} ({len(content) / 1e6:.1f} MB)")

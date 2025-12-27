"""
Convert 1km GHSL-POP rasters to H3 resolution 8.

Purpose: Process all epochs in parallel on Modal using exactextract for
         accurate area-weighted zonal statistics. Only processes H3 cells
         that overlap with city geometries from geometries_by_epoch.parquet.
         Each H3 cell is associated with its primary city (largest overlap).

Usage:
  modal run src/s03_raster_1km_to_h3_r8.py              # Full pipeline
  modal run src/s03_raster_1km_to_h3_r8.py --skip-existing  # Resume processing
  modal run src/s03_raster_1km_to_h3_r8.py --build-only     # Build pop time series
  modal run src/s03_raster_1km_to_h3_r8.py --download-local # Download locally

Setup (one-time):
  1. Create R2 bucket in Cloudflare dashboard
  2. Create R2 API token with read/write permissions
  3. Create Modal secret:
     modal secret create r2-credentials \\
       R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com \\
       R2_ACCESS_KEY_ID=<your_access_key> \\
       R2_SECRET_ACCESS_KEY=<your_secret_key> \\
       R2_BUCKET_NAME=<your_bucket_name>

Cost estimate: ~$1-2 for all 12 epochs (parallel processing)
Time estimate: ~15-25 minutes wall-clock

Decision log:
  - Uses WGS84 GHSL data (4326_30ss) - no reprojection needed
  - Uses exactextract for proper area-weighted population sums
  - Only processes H3 cells overlapping city geometries
  - Uses per-epoch city boundaries from geometries_by_epoch.parquet (MTUC)
  - Each H3 cell assigned to primary city (largest intersection area)
  - Cell generation and processing combined in single function (no intermediate files)
  - All 12 epochs processed in parallel (12 containers @ 32GB each)

Date: 2025-12-13 (updated 2025-12-26)
"""

import modal

# Modal app setup
app = modal.App("ghsl-h3-conversion")

# Container image with all dependencies
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

# Volume for persisting results
volume = modal.Volume.from_name("ghsl-h3-results", create_if_missing=True)

# Constants
GHSL_URL_TEMPLATE = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_POP_GLOBE_R2023A/GHS_POP_E{epoch}_GLOBE_R2023A_4326_30ss/V1-0/"
    "GHS_POP_E{epoch}_GLOBE_R2023A_4326_30ss_V1_0.zip"
)
EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
H3_RESOLUTION = 8
EPOCH_GEOMETRIES_PARQUET = "data/interim/mtuc/geometries_by_epoch.parquet"


@app.function(
    image=image,
    memory=32768,  # 32GB for raster + exactextract + H3 cells
    cpu=2.0,
    timeout=3600,  # 60 minutes max per epoch
    retries=2,
    volumes={"/results": volume},
)
def process_epoch_full(epoch_geom_bytes: bytes, epoch: int) -> str:
    """
    Generate H3 cells and process population for a single epoch.

    Combines cell generation and raster processing in a single function
    to enable full parallelism across all epochs (no sequential phases).

    Each H3 cell is associated with its primary city (the one with the
    largest intersection area when a cell overlaps multiple cities).

    Args:
        epoch_geom_bytes: Serialized geometries_by_epoch.parquet content
        epoch: Year to filter geometries (1975, 1980, ..., 2030)

    Returns:
        Status message with cell count
    """
    import io
    import tempfile
    import zipfile
    from collections import defaultdict
    from pathlib import Path

    import geopandas as gpd
    import h3
    import httpx
    import polars as pl
    from exactextract import exact_extract
    from shapely import Polygon

    print(f"[{epoch}] Starting full processing...")

    # =========================================================================
    # Step 1: Generate H3 cells from city geometries (in-memory)
    # =========================================================================
    print(f"[{epoch}] Loading epoch geometries from parquet...")
    all_geom_gdf = gpd.read_parquet(io.BytesIO(epoch_geom_bytes))

    # Filter to this epoch
    epoch_gdf = all_geom_gdf[all_geom_gdf["epoch"] == epoch].copy()
    print(f"[{epoch}] Filtered to {len(epoch_gdf):,} cities for epoch {epoch}")

    if len(epoch_gdf) == 0:
        print(f"[{epoch}] No geometries found for epoch {epoch}")
        return f"No geometries for epoch {epoch}"

    # Generate H3 cells for each city geometry, tracking overlap areas
    # Map: h3_index -> [(city_id, overlap_area), ...]
    print(f"[{epoch}] Generating H3 res {H3_RESOLUTION} cells with city associations...")
    cell_city_overlaps: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for idx, row in enumerate(epoch_gdf.itertuples()):
        geometry = row.geometry
        city_id = str(row.city_id)

        if geometry is None or geometry.is_empty:
            continue
        try:
            cells = h3.geo_to_cells(geometry, res=H3_RESOLUTION)
            for cell in cells:
                # Compute intersection area between H3 cell and city geometry
                boundary = h3.cell_to_boundary(cell)
                coords = [(lng, lat) for lat, lng in boundary]
                coords.append(coords[0])
                cell_polygon = Polygon(coords)

                intersection = cell_polygon.intersection(geometry)
                overlap_area = intersection.area if not intersection.is_empty else 0.0
                cell_city_overlaps[cell].append((city_id, overlap_area))
        except Exception as e:
            print(f"[{epoch}] Warning: Failed to process city {city_id}: {e}")
            continue

        if (idx + 1) % 1000 == 0:
            print(f"[{epoch}] Processed {idx + 1:,} cities, {len(cell_city_overlaps):,} unique cells")

    print(f"[{epoch}] Total unique H3 cells: {len(cell_city_overlaps):,}")

    # Assign each cell to the city with the largest overlap
    print(f"[{epoch}] Assigning cells to primary cities...")
    h3_cells = []
    for i, (cell, city_overlaps) in enumerate(cell_city_overlaps.items()):
        # Select city with maximum overlap area
        primary_city_id = max(city_overlaps, key=lambda x: x[1])[0]

        boundary = h3.cell_to_boundary(cell)
        coords = [(lng, lat) for lat, lng in boundary]
        coords.append(coords[0])
        h3_cells.append({
            "h3_index": cell,
            "city_id": primary_city_id,
            "geometry": Polygon(coords),
        })

        if (i + 1) % 100000 == 0:
            print(f"[{epoch}] Assigned {i + 1:,} cells")

    # Create GeoDataFrame (in-memory, not saved)
    h3_cells_gdf = gpd.GeoDataFrame(h3_cells, crs="EPSG:4326")
    print(f"[{epoch}] Created {len(h3_cells_gdf):,} H3 cell polygons in memory")

    # =========================================================================
    # Step 2: Download and process raster
    # =========================================================================
    url = GHSL_URL_TEMPLATE.format(epoch=epoch)
    print(f"[{epoch}] Downloading raster from {url}")

    with httpx.Client(timeout=600) as client:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        zip_bytes = response.content

    print(f"[{epoch}] Downloaded {len(zip_bytes) / 1e6:.1f} MB")

    # Extract tif from zip
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            tif_names = [n for n in zf.namelist() if n.endswith(".tif")]
            if not tif_names:
                raise ValueError(f"No .tif file found in archive for {epoch}")

            tif_name = tif_names[0]
            zf.extract(tif_name, tmppath)
            tif_path = tmppath / tif_name

        print(f"[{epoch}] Extracted {tif_name}")

        # Run exactextract with area-weighted sum
        print(f"[{epoch}] Running exactextract (sum aggregation)...")
        results_df = exact_extract(
            str(tif_path),
            h3_cells_gdf,
            ops=["sum"],
            include_cols=["h3_index", "city_id"],
            output="pandas",
        )

        # Convert to polars and rename
        df = pl.from_pandas(results_df).rename({"sum": "population"})

        # Convert h3_index from string back to int64
        df = df.with_columns(
            pl.col("h3_index").map_elements(h3.str_to_int, return_dtype=pl.Int64)
        )

        # Filter to positive population
        df = df.filter(pl.col("population") > 0)

        print(f"[{epoch}] Generated {len(df):,} H3 cells with population")

        # Save to volume
        results_dir = Path("/results")
        results_dir.mkdir(exist_ok=True)
        output_path = results_dir / f"h3_r8_pop_{epoch}.parquet"
        df.write_parquet(output_path)
        volume.commit()

        file_size = output_path.stat().st_size / 1e6
        print(f"[{epoch}] Complete! Saved {output_path.name} ({file_size:.1f} MB)")

        return f"Epoch {epoch}: {len(df):,} H3 cells saved"


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=600,
)
def build_pop_timeseries() -> str:
    """Build wide-format population time series from volume files."""
    import duckdb
    from pathlib import Path

    print("Building population time series table...")

    results_dir = Path("/results")

    # Find all epoch parquet files
    epoch_files = sorted(results_dir.glob("h3_r8_pop_[0-9][0-9][0-9][0-9].parquet"))
    epochs = [int(f.stem.split("_")[-1]) for f in epoch_files]

    if not epochs:
        return "No epoch files found in volume"

    print(f"  Found {len(epochs)} epoch files: {epochs}")

    # Build time series with DuckDB
    conn = duckdb.connect()
    union_parts = []
    for epoch in epochs:
        epoch_file = results_dir / f"h3_r8_pop_{epoch}.parquet"
        union_parts.append(
            f"SELECT h3_index, population, {epoch} as year FROM read_parquet('{epoch_file}')"
        )

    union_query = " UNION ALL ".join(union_parts)

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
    time_series_path = results_dir / "h3_r8_pop_timeseries.parquet"
    result.write_parquet(time_series_path)

    # Commit volume
    volume.commit()

    conn.close()

    return f"Saved h3_r8_pop_timeseries.parquet with {len(result):,} H3 cells"


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=60,
)
def list_existing_epochs() -> list[int]:
    """List epochs already processed in volume."""
    from pathlib import Path

    results_dir = Path("/results")
    existing = []
    for f in results_dir.glob("h3_r8_pop_[0-9][0-9][0-9][0-9].parquet"):
        existing.append(int(f.stem.split("_")[-1]))
    return sorted(existing)


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=600,  # 10 minutes for ~4GB transfer
)
def download_results() -> dict[str, bytes]:
    """Download all results from volume (for local storage)."""
    from pathlib import Path

    results_dir = Path("/results")
    files = {}

    for path in results_dir.glob("*.parquet"):
        files[path.name] = path.read_bytes()
        print(f"  Read {path.name}: {len(files[path.name]) / 1e6:.1f} MB")

    return files


@app.function(
    image=image,
    volumes={"/results": volume},
    secrets=[modal.Secret.from_name("r2-credentials")],
    timeout=600,  # 10 minutes for upload
)
def upload_to_r2(prefix: str = "ghsl-pop-1km") -> list[str]:
    """Upload all results from volume to R2."""
    import os
    from pathlib import Path

    import boto3

    # Get R2 credentials from environment (injected by Modal secret)
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

    for path in sorted(results_dir.glob("*.parquet")):
        key = f"{prefix}/{path.name}"
        file_size = path.stat().st_size / 1e6

        print(f"  Uploading {path.name} ({file_size:.1f} MB) -> {key}")
        s3.upload_file(str(path), bucket_name, key)
        uploaded.append(key)

    print(f"Uploaded {len(uploaded)} files to s3://{bucket_name}/{prefix}/")
    return uploaded


@app.local_entrypoint()
def main(
    skip_existing: bool = False,
    build_only: bool = False,
    download_local: bool = False,
    upload_only: bool = False,
):
    """Run the H3 conversion pipeline with exactextract.

    All 12 epochs are processed in parallel - each container generates H3 cells
    and processes the raster in a single step for maximum concurrency.

    Args:
        skip_existing: Skip epochs already in volume (for resuming)
        build_only: Only build pop time series from existing epoch files
        download_local: Download results to local disk instead of R2
        upload_only: Only upload existing results to R2 (skip processing)
    """
    import time
    from pathlib import Path

    print("=" * 60)
    print("1km Raster to H3 with exactextract (Modal Cloud)")
    print("=" * 60)

    start_time = time.time()

    # Upload-only mode: just upload existing files to R2
    if upload_only:
        print("\nUpload-only mode: uploading existing files to R2...")
        uploaded = upload_to_r2.remote()
        print(f"  Uploaded {len(uploaded)} files")
        total_time = time.time() - start_time
        print(f"\nComplete! Total time: {total_time:.1f}s")
        return

    # Build-only mode: just create time series from existing files
    if build_only:
        print("\nBuild-only mode: creating pop time series from existing epoch files...")
        summary = build_pop_timeseries.remote()
        print(f"  {summary}")

        if download_local:
            _download_to_local(Path("data/interim/h3_pop_1km"))
        else:
            print("\nUploading to R2...")
            uploaded = upload_to_r2.remote()
            print(f"  Uploaded {len(uploaded)} files")

        total_time = time.time() - start_time
        print(f"\nComplete! Total time: {total_time:.1f}s")
        return

    # Determine which epochs to process
    epochs_to_process = list(EPOCHS)

    # Check for existing epochs in volume
    if skip_existing:
        existing = list_existing_epochs.remote()
        if existing:
            print(f"  Found existing epochs in volume: {existing}")
            epochs_to_process = [e for e in epochs_to_process if e not in existing]
            if not epochs_to_process:
                print("  All epochs already processed! Use --build-only to create time series.")
                return

    print(f"\nProcessing {len(epochs_to_process)} epochs in parallel...")

    # Load geometry data
    geom_path = Path(EPOCH_GEOMETRIES_PARQUET)
    if not geom_path.exists():
        raise FileNotFoundError(
            f"Epoch geometries not found: {geom_path}\n"
            "Run 'uv run python -m src.s02b_extract_city_geometries' first."
        )
    geom_bytes = geom_path.read_bytes()
    print(f"Using per-epoch geometries from {geom_path} ({len(geom_bytes) / 1e6:.1f} MB)")

    # Process all epochs in parallel (single phase - cells + raster in each container)
    print(f"\nSpawning {len(epochs_to_process)} containers...")
    futures = []
    for epoch in epochs_to_process:
        futures.append(process_epoch_full.spawn(geom_bytes, epoch))

    # Wait for results
    for epoch, future in zip(epochs_to_process, futures):
        print(f"  Waiting for {epoch}...")
        status = future.get()
        print(f"    {status}")

    print(f"\nAll epochs processed in {time.time() - start_time:.1f}s")

    # Build pop time series
    print("\nBuilding pop time series...")
    summary = build_pop_timeseries.remote()
    print(f"  {summary}")

    # Upload to R2 or download locally
    if download_local:
        _download_to_local(Path("data/interim/h3_pop_1km"))
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

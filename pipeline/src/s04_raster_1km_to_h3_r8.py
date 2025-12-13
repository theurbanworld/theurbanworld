"""
04 - Convert 1km GHSL-POP rasters to H3 resolution 8.

Purpose: Process all epochs in parallel on Modal using exactextract for
         accurate area-weighted zonal statistics. Only processes H3 cells
         that overlap with city geometries from cities.parquet.

Usage:
  modal run src/s04_raster_1km_to_h3_r8.py              # Full pipeline
  modal run src/s04_raster_1km_to_h3_r8.py --test       # Single epoch (2020)
  modal run src/s04_raster_1km_to_h3_r8.py --zones-only # Generate H3 zones only
  modal run src/s04_raster_1km_to_h3_r8.py --skip-zones # Use existing zones
  modal run src/s04_raster_1km_to_h3_r8.py --skip-existing  # Resume processing
  modal run src/s04_raster_1km_to_h3_r8.py --build-only     # Build time series
  modal run src/s04_raster_1km_to_h3_r8.py --download-local # Download locally

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
Time estimate: ~30-45 minutes wall-clock

Decision log:
  - Uses WGS84 GHSL data (4326_30ss) - no reprojection needed
  - Uses exactextract for proper area-weighted population sums
  - Only processes H3 cells overlapping city geometries (from cities.parquet)
  - H3 zones generated once and cached in Modal volume
  - Process epochs in parallel (12 containers)
  - 32GB memory per container for raster + exactextract
Date: 2024-12-13
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
CITIES_PARQUET = "data/interim/cities.parquet"


@app.function(
    image=image,
    memory=16384,  # 16GB for H3 cell generation
    timeout=1800,  # 30 minutes
    volumes={"/results": volume},
)
def generate_h3_zones(cities_bytes: bytes) -> str:
    """
    Generate H3 res 8 polygon zones for all city geometries.

    Args:
        cities_bytes: Serialized cities.parquet content

    Returns:
        Status message with cell count
    """
    import io
    from pathlib import Path

    import geopandas as gpd
    import h3
    from shapely import Polygon

    print("Loading cities from parquet...")
    cities_gdf = gpd.read_parquet(io.BytesIO(cities_bytes))
    print(f"  Loaded {len(cities_gdf):,} cities")

    # Generate H3 cells for each city geometry
    print(f"Generating H3 res {H3_RESOLUTION} cells for city geometries...")
    all_cells = set()
    for idx, geometry in enumerate(cities_gdf.geometry):
        if geometry is None or geometry.is_empty:
            continue
        try:
            # h3.geo_to_cells expects a GeoJSON-like __geo_interface__
            cells = h3.geo_to_cells(geometry, res=H3_RESOLUTION)
            all_cells.update(cells)
        except Exception as e:
            print(f"  Warning: Failed to process geometry {idx}: {e}")
            continue

        if (idx + 1) % 1000 == 0:
            print(f"  Processed {idx + 1:,} cities, {len(all_cells):,} unique cells so far")

    print(f"  Total unique H3 cells: {len(all_cells):,}")

    # Convert cells to polygons for exactextract
    # Store h3_index as string to avoid exactextract C++ type casting issues
    print("Converting H3 cells to polygons...")
    h3_polygons = []
    for i, cell in enumerate(all_cells):
        boundary = h3.cell_to_boundary(cell)
        # boundary is [(lat, lng), ...], convert to [(lng, lat), ...] for shapely
        coords = [(lng, lat) for lat, lng in boundary]
        coords.append(coords[0])  # Close polygon
        h3_polygons.append({
            "h3_index": cell,  # Keep as string for exactextract compatibility
            "geometry": Polygon(coords),
        })

        if (i + 1) % 100000 == 0:
            print(f"  Converted {i + 1:,} polygons")

    # Create GeoDataFrame
    print("Creating GeoDataFrame...")
    zones_gdf = gpd.GeoDataFrame(h3_polygons, crs="EPSG:4326")

    # Save to volume
    output_path = Path("/results/h3_zones.parquet")
    zones_gdf.to_parquet(output_path)
    volume.commit()

    file_size = output_path.stat().st_size / 1e6
    print(f"Saved {output_path.name} ({file_size:.1f} MB)")

    return f"Generated {len(zones_gdf):,} H3 zones"


@app.function(
    image=image,
    memory=32768,  # 32GB for raster + exactextract
    cpu=2.0,
    timeout=3600,  # 60 minutes max per epoch
    retries=2,
    volumes={"/results": volume},
)
def process_epoch(epoch: int) -> str:
    """Process a single epoch using exactextract for area-weighted zonal statistics."""
    import io
    import tempfile
    import zipfile
    from pathlib import Path

    import geopandas as gpd
    import httpx
    import polars as pl
    from exactextract import exact_extract

    print(f"[{epoch}] Starting processing...")

    # Load H3 zones from volume
    zones_path = Path("/results/h3_zones.parquet")
    if not zones_path.exists():
        raise RuntimeError("H3 zones not found - run generate_h3_zones first")

    print(f"[{epoch}] Loading H3 zones...")
    zones_gdf = gpd.read_parquet(zones_path)
    print(f"[{epoch}] Loaded {len(zones_gdf):,} H3 zones")

    # Download the WGS84 raster (no reprojection needed)
    url = GHSL_URL_TEMPLATE.format(epoch=epoch)
    print(f"[{epoch}] Downloading from {url}")

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
            zones_gdf,
            ops=["sum"],
            include_cols=["h3_index"],
            output="pandas",
        )

        # Convert to polars and rename
        df = pl.from_pandas(results_df).rename({"sum": "population"})

        # Convert h3_index from string back to int64
        import h3
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

        return f"Saved {len(df):,} cells to {output_path.name}"


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=600,
)
def build_time_series() -> str:
    """Build wide-format time series from volume files."""
    import duckdb
    from pathlib import Path

    print("Building time series table...")

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
    timeout=60,
)
def check_zones_exist() -> bool:
    """Check if H3 zones file exists in volume."""
    from pathlib import Path

    zones_path = Path("/results/h3_zones.parquet")
    return zones_path.exists()


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
    local: bool = False,
    test: bool = False,
    skip_existing: bool = False,
    build_only: bool = False,
    download_local: bool = False,
    upload_only: bool = False,
    zones_only: bool = False,
    skip_zones: bool = False,
    regenerate_zones: bool = False,
):
    """Run the H3 conversion pipeline with exactextract.

    Args:
        local: Run locally (no cloud) with single epoch
        test: Run in cloud but only process 2020 epoch (cheaper test)
        skip_existing: Skip epochs already in volume (for resuming)
        build_only: Only build time series from existing epoch files
        download_local: Download results to local disk instead of R2
        upload_only: Only upload existing results to R2 (skip processing)
        zones_only: Only generate H3 zones from cities (skip epoch processing)
        skip_zones: Skip zone generation (use existing zones in volume)
        regenerate_zones: Force regenerate zones even if they exist
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
        print("\nBuild-only mode: creating time series from existing epoch files...")
        summary = build_time_series.remote()
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

    # Load cities.parquet for zone generation
    cities_path = Path(CITIES_PARQUET)
    if not cities_path.exists():
        raise FileNotFoundError(f"Cities file not found: {cities_path}")

    cities_bytes = cities_path.read_bytes()
    print(f"\nLoaded {cities_path} ({len(cities_bytes) / 1e6:.1f} MB)")

    # Generate H3 zones (or skip if requested)
    if not skip_zones:
        if regenerate_zones:
            print("\nRegenerating H3 zones (--regenerate-zones)...")
            zones_status = generate_h3_zones.remote(cities_bytes)
            print(f"  {zones_status}")
        else:
            # Check if zones exist
            existing_zones = check_zones_exist.remote()
            if existing_zones:
                print("\nH3 zones already exist in volume (use --regenerate-zones to recreate)")
            else:
                print("\nGenerating H3 zones from city geometries...")
                zones_status = generate_h3_zones.remote(cities_bytes)
                print(f"  {zones_status}")

    # Zones-only mode: stop after zone generation
    if zones_only:
        total_time = time.time() - start_time
        print(f"\nZones-only mode complete! Total time: {total_time:.1f}s")
        return

    # Determine which epochs to process
    if local or test:
        epochs_to_process = [2020]  # Single epoch for testing
        print(f"\n{'Local' if local else 'Cloud'} test mode: processing only 2020")
    else:
        epochs_to_process = list(EPOCHS)
        print(f"\nProcessing {len(epochs_to_process)} epochs...")

    # Check for existing epochs in volume
    if skip_existing and not local:
        existing = list_existing_epochs.remote()
        if existing:
            print(f"  Found existing epochs in volume: {existing}")
            epochs_to_process = [e for e in epochs_to_process if e not in existing]
            if not epochs_to_process:
                print("  All epochs already processed! Use --build-only to create time series.")
                return
            print(f"  Will process remaining epochs: {epochs_to_process}")

    if local:
        # Local test (no cloud)
        result = process_epoch.local(2020)
        print(f"  {result}")
    else:
        # Cloud processing (parallel)
        futures = []
        for epoch in epochs_to_process:
            futures.append(process_epoch.spawn(epoch))

        # Wait for results (just status messages, data saved to volume)
        for epoch, future in zip(epochs_to_process, futures):
            print(f"  Waiting for {epoch}...")
            status = future.get()
            print(f"    {status}")

    print(f"\nAll epochs processed in {time.time() - start_time:.1f}s")

    # Build time series
    print("\nBuilding time series...")
    summary = build_time_series.remote()
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

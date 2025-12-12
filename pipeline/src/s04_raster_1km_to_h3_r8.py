"""
04 - Convert 1km GHSL-POP rasters to H3 resolution 8.

Purpose: Process all epochs in parallel on Modal for faster execution
Usage:
  modal run src/s04_raster_1km_to_h3_r8.py  # Process and upload to R2
  modal run src/s04_raster_1km_to_h3_r8.py --skip-existing  # Resume
  modal run src/s04_raster_1km_to_h3_r8.py --build-only  # Just build time series
  modal run src/s04_raster_1km_to_h3_r8.py --download-local  # Download to local disk

Setup (one-time):
  1. Create R2 bucket in Cloudflare dashboard
  2. Create R2 API token with read/write permissions
  3. Create Modal secret:
     modal secret create r2-credentials \\
       R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com \\
       R2_ACCESS_KEY_ID=<your_access_key> \\
       R2_SECRET_ACCESS_KEY=<your_secret_key> \\
       R2_BUCKET_NAME=<your_bucket_name>

Cost estimate: ~$0.50-1.00 for all 10 epochs (parallel processing)
Time estimate: ~15-25 minutes wall-clock

Decision log:
  - Process epochs in parallel (10 containers)
  - 32GB memory per container to avoid tiling overhead
  - Download data directly in container (faster than mounting)
  - Results saved to Modal volume, then uploaded to R2
Date: 2024-12-10
"""

import modal

# Modal app setup
app = modal.App("ghsl-h3-conversion")

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
volume = modal.Volume.from_name("ghsl-h3-results", create_if_missing=True)

# Constants
GHSL_URL_TEMPLATE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000/V1-0/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000_V1_0.zip"
EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
H3_RESOLUTION = 8  # Res 8 (~0.7 km²) matches 1km input data better than res 9 (~0.1 km²)


@app.function(
    image=image,
    memory=32768,  # 32GB - enough to process without tiling
    cpu=2.0,       # Request 2 CPUs for faster H3 conversion
    timeout=3600,  # 60 minutes max per epoch
    retries=2,
    volumes={"/results": volume},
)
def process_epoch(epoch: int) -> str:
    """Process a single epoch and save to volume."""
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

    print(f"[{epoch}] Starting processing...")

    # Download the file
    url = GHSL_URL_TEMPLATE.format(epoch=epoch)
    print(f"[{epoch}] Downloading from {url}")

    with httpx.Client(timeout=300) as client:
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

        # Load raster
        data = xr.open_dataarray(tif_path, engine="rasterio")
        nodata = data.rio.nodata or -200.0

        print(f"[{epoch}] Loaded raster: shape={data.shape}, crs={data.rio.crs}")

        # Reproject to WGS84
        print(f"[{epoch}] Reprojecting to WGS84...")
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

        print(f"[{epoch}] Converting to H3 res {H3_RESOLUTION}... (shape: {values.shape})")

        # Convert to H3 (with full memory, no tiling needed)
        table = raster_to_dataframe(
            values,
            transform,
            H3_RESOLUTION,
            nodata_value=float(nodata),
            compact=False,
        )

        # Convert to polars
        df = pl.from_arrow(table).rename({"cell": "h3_index", "value": "population"})

        # Filter
        df = df.filter(pl.col("population") > 0)

        print(f"[{epoch}] Generated {len(df):,} H3 cells")

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
):
    """Run the H3 conversion pipeline.

    Args:
        local: Run locally (no cloud) with single epoch
        test: Run in cloud but only process 2020 epoch (cheaper test)
        skip_existing: Skip epochs already in volume (for resuming)
        build_only: Only build time series from existing epoch files
        download_local: Download results to local disk instead of R2
        upload_only: Only upload existing results to R2 (skip processing)
    """
    import time
    from pathlib import Path

    print("=" * 60)
    print("1km Raster to H3 (Modal Cloud)")
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

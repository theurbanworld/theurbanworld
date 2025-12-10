"""
04 - Convert 1km GHSL-POP rasters to H3 (Modal cloud version).

Purpose: Process all epochs in parallel on Modal for faster execution
Usage:
  modal run src/s04_raster_to_h3_1km_modal.py  # Run in cloud
  modal run src/s04_raster_to_h3_1km_modal.py --local  # Test locally

Cost estimate: ~$0.50-1.00 for all 10 epochs (parallel processing)
Time estimate: ~10-20 minutes wall-clock

Decision log:
  - Process epochs in parallel (10 containers)
  - 32GB memory per container to avoid tiling overhead
  - Download data directly in container (faster than mounting)
  - Write results to Modal volume, then download locally
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
    )
)

# Volume for persisting results
volume = modal.Volume.from_name("ghsl-h3-results", create_if_missing=True)

# Constants
GHSL_URL_TEMPLATE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000/V1-0/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000_V1_0.zip"
EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]
H3_RESOLUTION = 8  # Res 8 (~0.7 km²) matches 1km input data better than res 9 (~0.1 km²)


@app.function(
    image=image,
    memory=32768,  # 32GB - enough to process without tiling
    cpu=2.0,       # Request 2 CPUs for faster H3 conversion
    timeout=3600,  # 60 minutes max per epoch
    retries=2,
)
def process_epoch(epoch: int) -> bytes:
    """Process a single epoch and return parquet bytes."""
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

        # Serialize to parquet bytes
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        parquet_bytes = buffer.getvalue()

        print(f"[{epoch}] Complete! Parquet size: {len(parquet_bytes) / 1e6:.1f} MB")

        return parquet_bytes


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=600,
)
def build_time_series(epoch_results: dict[int, bytes]) -> str:
    """Build wide-format time series from epoch results."""
    import duckdb
    import polars as pl
    from pathlib import Path

    print("Building time series table...")

    results_dir = Path("/results")
    results_dir.mkdir(exist_ok=True)

    # Save individual epoch files
    for epoch, parquet_bytes in epoch_results.items():
        epoch_path = results_dir / f"{epoch}.parquet"
        epoch_path.write_bytes(parquet_bytes)
        print(f"  Saved {epoch}.parquet")

    # Build time series with DuckDB
    conn = duckdb.connect()

    epochs = sorted(epoch_results.keys())
    union_parts = []
    for epoch in epochs:
        epoch_file = results_dir / f"{epoch}.parquet"
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
    time_series_path = results_dir / "time_series.parquet"
    result.write_parquet(time_series_path)

    # Commit volume
    volume.commit()

    conn.close()

    return f"Saved time_series.parquet with {len(result):,} H3 cells"


@app.function(
    image=image,
    volumes={"/results": volume},
    timeout=300,
)
def download_results() -> dict[str, bytes]:
    """Download all results from volume."""
    from pathlib import Path

    results_dir = Path("/results")
    files = {}

    for path in results_dir.glob("*.parquet"):
        files[path.name] = path.read_bytes()
        print(f"  Read {path.name}: {len(files[path.name]) / 1e6:.1f} MB")

    return files


@app.local_entrypoint()
def main(local: bool = False, test: bool = False):
    """Run the H3 conversion pipeline.

    Args:
        local: Run locally (no cloud) with single epoch
        test: Run in cloud but only process 2020 epoch (cheaper test)
    """
    import time
    from pathlib import Path

    print("=" * 60)
    print("1km Raster to H3 (Modal Cloud)")
    print("=" * 60)

    start_time = time.time()

    # Determine which epochs to process
    if local or test:
        epochs_to_process = [2020]  # Single epoch for testing
        print(f"\n{'Local' if local else 'Cloud'} test mode: processing only 2020")
    else:
        epochs_to_process = EPOCHS
        print(f"\nProcessing {len(epochs_to_process)} epochs in parallel...")

    if local:
        # Local test (no cloud)
        result = process_epoch.local(2020)
        epoch_results = {2020: result}
    else:
        # Cloud processing (parallel)
        futures = []
        for epoch in epochs_to_process:
            futures.append(process_epoch.spawn(epoch))

        # Collect results
        epoch_results = {}
        for epoch, future in zip(epochs_to_process, futures):
            print(f"  Waiting for {epoch}...")
            epoch_results[epoch] = future.get()

    print(f"\nAll epochs processed in {time.time() - start_time:.1f}s")

    # Build time series
    print("\nBuilding time series...")
    summary = build_time_series.remote(epoch_results)
    print(f"  {summary}")

    # Download results locally
    print("\nDownloading results...")
    files = download_results.remote()

    # Save to local data directory
    output_dir = Path("data/interim/h3_pop_1km")
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in files.items():
        output_path = output_dir / filename
        output_path.write_bytes(content)
        print(f"  Saved {output_path}")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Complete! Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Results saved to {output_dir}")
    print("=" * 60)

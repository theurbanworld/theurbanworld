"""
Extract per-city H3 data from the global H3 timeseries.

Purpose: Using the global H3-R8 population timeseries (from modal_global_h3_r8.py),
         extract per-city data including buffer zones, proto-city/post-city
         populations, and per-epoch population-weighted centroids.

Outputs:
  1. Per-city JSON files (R2): city_h3/{city_id}.json
     {"cells": [{"h": "882f...", "p": [0, 0, 120, ...]}]}
  2. Proto/post-city populations: proto_city_populations.parquet
  3. Per-epoch centroids: city_centroids_h3_r8.parquet

Usage:
  # One-time: upload city data to volume (run from main working copy with data/)
  modal run src/h3/modal_extract_city_h3.py --prepare

  # Process (can run from anywhere — reads from volumes)
  modal run src/h3/modal_extract_city_h3.py
  modal run src/h3/modal_extract_city_h3.py --upload-only

Prerequisites:
  - Global timeseries on Modal volume (run modal_global_h3_r8.py first)
  - City data on volume (run --prepare once from repo with data/ dir)

Date: 2026-03-30
"""

import modal

app = modal.App("ghsl-city-h3-extract")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgdal-dev", "gdal-bin")
    .pip_install(
        "geopandas>=1.0.0",
        "h3>=4.0.0",
        "pyarrow>=15.0.0",
        "polars>=1.0.0",
        "duckdb>=1.0.0",
        "numpy>=1.26.0",
        "boto3>=1.35.0",
        "shapely>=2.0.0",
        "orjson>=3.9.0",
    )
)

# Shared volume with global H3 data from Phase 1
global_volume = modal.Volume.from_name("ghsl-global-h3-results")
# Output volume for city extracts (also stores input city data)
city_volume = modal.Volume.from_name("ghsl-city-h3-results", create_if_missing=True)

EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
H3_RESOLUTION = 8
BUFFER_KM = 30.0

# Paths on the city volume for input data
VOLUME_CITIES_PATH = "/results/input/cities.parquet"
VOLUME_GEOM_PATH = "/results/input/geometries_by_epoch.parquet"


# ─── Prepare: upload city data to volume ──────────────────────────────────────


@app.function(
    image=image,
    memory=4096,
    timeout=300,
    volumes={"/results": city_volume},
)
def upload_city_data(cities_bytes: bytes, geom_bytes: bytes) -> str:
    """Store cities.parquet and geometries_by_epoch.parquet on the volume."""
    from pathlib import Path

    input_dir = Path("/results/input")
    input_dir.mkdir(parents=True, exist_ok=True)

    cities_path = input_dir / "cities.parquet"
    cities_path.write_bytes(cities_bytes)

    geom_path = input_dir / "geometries_by_epoch.parquet"
    geom_path.write_bytes(geom_bytes)

    city_volume.commit()

    return (
        f"Uploaded cities.parquet ({len(cities_bytes) / 1e6:.1f} MB) "
        f"and geometries_by_epoch.parquet ({len(geom_bytes) / 1e6:.1f} MB)"
    )


@app.function(
    image=image,
    memory=4096,
    timeout=60,
    volumes={"/results": city_volume},
)
def check_city_data() -> dict:
    """Check if city data exists on the volume. Returns file info."""
    from pathlib import Path

    result = {}
    for name, path in [("cities", VOLUME_CITIES_PATH), ("geometries", VOLUME_GEOM_PATH)]:
        p = Path(path)
        if p.exists():
            result[name] = {"exists": True, "size_mb": round(p.stat().st_size / 1e6, 1)}
        else:
            result[name] = {"exists": False}
    return result


# ─── Process city batches ─────────────────────────────────────────────────────


@app.function(
    image=image,
    memory=65536,  # 64GB — loads full global timeseries
    cpu=4.0,
    timeout=7200,
    volumes={"/global": global_volume, "/results": city_volume},
)
def process_city_batch(
    city_ids: list[str],
    buffer_km: float = BUFFER_KM,
) -> str:
    """
    Process a batch of cities: extract buffered H3 data, proto/post-city
    populations, and per-epoch centroids.

    Reads city data from the volume (uploaded via --prepare).
    """
    import math
    from pathlib import Path

    import geopandas as gpd
    import h3
    import polars as pl
    from shapely import unary_union

    # ── Load data from volumes ──
    print(f"Processing batch of {len(city_ids)} cities...")

    cities_gdf = gpd.read_parquet(VOLUME_CITIES_PATH)
    geom_gdf = gpd.read_parquet(VOLUME_GEOM_PATH)

    # Load global timeseries
    ts_path = Path("/global/global_h3_r8_pop_timeseries.parquet")
    if not ts_path.exists():
        return "ERROR: Global timeseries not found on volume"

    print("  Loading global timeseries...")
    ts_df = pl.read_parquet(ts_path)

    # Build lookup: h3_index (int64) -> [pop_1975, pop_1980, ..., pop_2030]
    pop_cols = [f"pop_{e}" for e in EPOCHS]
    ts_dict = {}
    for row in ts_df.iter_rows(named=True):
        ts_dict[row["h3_index"]] = [row[c] for c in pop_cols]

    print(f"  Loaded {len(ts_dict):,} cells in timeseries")

    # Prepare output directories
    json_dir = Path("/results/city_h3")
    json_dir.mkdir(parents=True, exist_ok=True)

    proto_rows = []
    centroid_rows = []

    for city_id in city_ids:
        city_row = cities_gdf[cities_gdf["city_id"] == city_id]
        if city_row.empty:
            continue

        city = city_row.iloc[0]
        birth_year = city.get("ucdb_year_of_birth")
        if birth_year is not None and hasattr(birth_year, "item"):
            birth_year = int(birth_year)

        # Get all epoch geometries for this city
        city_geoms = geom_gdf[geom_gdf["city_id"] == city_id]
        city_epochs = sorted(city_geoms["epoch"].unique())

        if not city_epochs:
            continue

        # Derive death year: first epoch AFTER the last alive epoch
        max_alive_epoch = max(city_epochs)
        death_year = None
        if max_alive_epoch < 2030:
            idx = EPOCHS.index(max_alive_epoch)
            if idx + 1 < len(EPOCHS):
                death_year = EPOCHS[idx + 1]

        # ── 1. Per-city H3 extract with buffer ──
        all_geoms = city_geoms.geometry.tolist()
        union_geom = unary_union(all_geoms)

        # Buffer in approximate degrees (1° lat ≈ 111 km)
        buffer_deg = buffer_km / 111.0
        buffered_geom = union_geom.buffer(buffer_deg)

        try:
            buffered_cells = h3.geo_to_cells(buffered_geom.__geo_interface__, res=H3_RESOLUTION)
        except Exception:
            try:
                buffered_cells = h3.geo_to_cells(union_geom.__geo_interface__, res=H3_RESOLUTION)
            except Exception:
                continue

        if not buffered_cells:
            continue

        # Look up population timeseries for each cell
        cell_data = []
        for cell_hex in buffered_cells:
            cell_int = h3.str_to_int(cell_hex)
            pops = ts_dict.get(cell_int)
            if pops is None:
                continue
            if any(p > 0 for p in pops):
                cell_data.append({"h": cell_hex, "p": [round(p, 1) for p in pops]})

        # Write per-city JSON
        if cell_data:
            output = {"cells": cell_data}
            json_path = json_dir / f"{city_id}.json"
            json_path.write_bytes(
                __import__("orjson").dumps(output)
            )

        # ── 2. Proto-city / post-city populations ──
        if birth_year and birth_year > 1975:
            birth_geom_row = city_geoms[city_geoms["epoch"] == birth_year]
            if not birth_geom_row.empty:
                birth_geom = birth_geom_row.iloc[0].geometry
                try:
                    proto_cells = h3.geo_to_cells(birth_geom.__geo_interface__, res=H3_RESOLUTION)
                except Exception:
                    proto_cells = set()

                for epoch_idx, epoch in enumerate(EPOCHS):
                    if epoch >= birth_year:
                        break
                    total_pop = 0.0
                    cell_count = 0
                    for cell_hex in proto_cells:
                        cell_int = h3.str_to_int(cell_hex)
                        pops = ts_dict.get(cell_int)
                        if pops and pops[epoch_idx] > 0:
                            total_pop += pops[epoch_idx]
                            cell_count += 1

                    area_km2 = cell_count * h3.average_hexagon_area(H3_RESOLUTION, unit="km^2")
                    proto_rows.append({
                        "city_id": city_id,
                        "epoch": epoch,
                        "population": round(total_pop, 1),
                        "area_km2": round(area_km2, 2),
                        "density_per_km2": round(total_pop / area_km2, 1) if area_km2 > 0 else 0.0,
                        "cell_count": cell_count,
                        "state": "proto",
                    })

        if death_year and death_year <= 2030:
            last_geom_row = city_geoms[city_geoms["epoch"] == max_alive_epoch]
            if not last_geom_row.empty:
                last_geom = last_geom_row.iloc[0].geometry
                try:
                    post_cells = h3.geo_to_cells(last_geom.__geo_interface__, res=H3_RESOLUTION)
                except Exception:
                    post_cells = set()

                for epoch_idx, epoch in enumerate(EPOCHS):
                    if epoch < death_year:
                        continue
                    total_pop = 0.0
                    cell_count = 0
                    for cell_hex in post_cells:
                        cell_int = h3.str_to_int(cell_hex)
                        pops = ts_dict.get(cell_int)
                        if pops and pops[epoch_idx] > 0:
                            total_pop += pops[epoch_idx]
                            cell_count += 1

                    area_km2 = cell_count * h3.average_hexagon_area(H3_RESOLUTION, unit="km^2")
                    proto_rows.append({
                        "city_id": city_id,
                        "epoch": epoch,
                        "population": round(total_pop, 1),
                        "area_km2": round(area_km2, 2),
                        "density_per_km2": round(total_pop / area_km2, 1) if area_km2 > 0 else 0.0,
                        "cell_count": cell_count,
                        "state": "post",
                    })

        # ── 3. Per-epoch centroids ──
        for epoch in city_epochs:
            epoch_idx = EPOCHS.index(epoch)
            epoch_geom_row = city_geoms[city_geoms["epoch"] == epoch]
            if epoch_geom_row.empty:
                continue

            epoch_geom = epoch_geom_row.iloc[0].geometry
            try:
                epoch_cells = h3.geo_to_cells(epoch_geom.__geo_interface__, res=H3_RESOLUTION)
            except Exception:
                continue

            if not epoch_cells:
                continue

            # Population-weighted centroid using 3D Cartesian averaging
            total_pop = 0.0
            x_sum = y_sum = z_sum = 0.0
            for cell_hex in epoch_cells:
                cell_int = h3.str_to_int(cell_hex)
                pops = ts_dict.get(cell_int)
                pop = pops[epoch_idx] if pops else 0.0
                if pop <= 0:
                    continue

                lat, lng = h3.cell_to_latlng(cell_hex)
                lat_rad = math.radians(lat)
                lng_rad = math.radians(lng)

                x_sum += math.cos(lat_rad) * math.cos(lng_rad) * pop
                y_sum += math.cos(lat_rad) * math.sin(lng_rad) * pop
                z_sum += math.sin(lat_rad) * pop
                total_pop += pop

            if total_pop > 0:
                x_avg = x_sum / total_pop
                y_avg = y_sum / total_pop
                z_avg = z_sum / total_pop

                lng_center = math.degrees(math.atan2(y_avg, x_avg))
                hyp = math.sqrt(x_avg**2 + y_avg**2)
                lat_center = math.degrees(math.atan2(z_avg, hyp))
            else:
                centroid = epoch_geom.centroid
                lat_center, lng_center = centroid.y, centroid.x

            # Snap to nearest H3 cell
            centroid_h3 = h3.latlng_to_cell(lat_center, lng_center, H3_RESOLUTION)
            snap_lat, snap_lng = h3.cell_to_latlng(centroid_h3)

            centroid_rows.append({
                "city_id": city_id,
                "epoch": epoch,
                "centroid_h3": centroid_h3,
                "centroid_lat": round(snap_lat, 6),
                "centroid_lng": round(snap_lng, 6),
            })

    # ── Save batch results ──
    batch_id = city_ids[0] if city_ids else "unknown"

    if proto_rows:
        proto_df = pl.DataFrame(proto_rows)
        proto_path = Path(f"/results/proto/batch_{batch_id}.parquet")
        proto_path.parent.mkdir(parents=True, exist_ok=True)
        proto_df.write_parquet(proto_path)

    if centroid_rows:
        centroid_df = pl.DataFrame(centroid_rows)
        centroid_path = Path(f"/results/centroids/batch_{batch_id}.parquet")
        centroid_path.parent.mkdir(parents=True, exist_ok=True)
        centroid_df.write_parquet(centroid_path)

    city_volume.commit()

    return (
        f"Batch {batch_id}: {len(city_ids)} cities, "
        f"{len(proto_rows)} proto/post rows, "
        f"{len(centroid_rows)} centroid rows"
    )


# ─── Get city IDs from volume ────────────────────────────────────────────────


@app.function(
    image=image,
    memory=4096,
    timeout=300,
    volumes={"/results": city_volume},
)
def get_city_ids() -> list[str]:
    """Read city IDs from cities.parquet on the volume."""
    import geopandas as gpd

    gdf = gpd.read_parquet(VOLUME_CITIES_PATH)
    return sorted(gdf["city_id"].astype(str).tolist())


# ─── Merge + upload ──────────────────────────────────────────────────────────


@app.function(
    image=image,
    memory=16384,
    cpu=2.0,
    timeout=1800,
    volumes={"/results": city_volume},
)
def merge_batch_results() -> str:
    """Merge per-batch proto-city and centroid parquets into single files."""
    from pathlib import Path

    import polars as pl

    results_dir = Path("/results")

    # Merge proto-city
    proto_files = sorted(results_dir.glob("proto/batch_*.parquet"))
    if proto_files:
        proto_df = pl.concat([pl.read_parquet(f) for f in proto_files])
        out = results_dir / "proto_city_populations.parquet"
        proto_df.write_parquet(out)
        print(f"Proto-city: {len(proto_df):,} rows -> {out.name}")
    else:
        print("No proto-city data found")

    # Merge centroids
    centroid_files = sorted(results_dir.glob("centroids/batch_*.parquet"))
    if centroid_files:
        centroid_df = pl.concat([pl.read_parquet(f) for f in centroid_files])
        out = results_dir / "city_centroids_h3_r8.parquet"
        centroid_df.write_parquet(out)
        print(f"Centroids: {len(centroid_df):,} rows -> {out.name}")
    else:
        print("No centroid data found")

    city_volume.commit()
    return "Merge complete"


@app.function(
    image=image,
    volumes={"/results": city_volume},
    secrets=[modal.Secret.from_name("r2-credentials")],
    timeout=7200,  # 2h — 11K+ small files
)
def upload_to_r2() -> list[str]:
    """Upload per-city JSON files and summary parquets to R2 (parallel)."""
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    from threading import Lock

    import boto3

    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["R2_BUCKET_NAME"]

    # Each thread gets its own client (boto3 clients are thread-safe but
    # a pool of clients avoids connection contention)
    def make_client():
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    results_dir = Path("/results")
    uploaded: list[str] = []
    upload_tasks: list[tuple[Path, str]] = []

    # Collect all files to upload
    json_dir = results_dir / "city_h3"
    if json_dir.exists():
        for path in json_dir.glob("*.json"):
            upload_tasks.append((path, f"data/city_h3/{path.name}"))

    for name in ["proto_city_populations.parquet", "city_centroids_h3_r8.parquet"]:
        path = results_dir / name
        if path.exists():
            upload_tasks.append((path, f"ghsl-city-h3/{name}"))

    print(f"Uploading {len(upload_tasks):,} files with 32 threads...")

    done_count = 0
    total = len(upload_tasks)
    from threading import Lock
    lock = Lock()

    def upload_one(item: tuple[Path, str]) -> str:
        nonlocal done_count
        path, key = item
        client = make_client()
        client.upload_file(str(path), bucket_name, key)
        with lock:
            done_count += 1
            if done_count % 1000 == 0 or done_count == total:
                print(f"  {done_count:,}/{total:,} uploaded")
        return key

    with ThreadPoolExecutor(max_workers=32) as pool:
        futures = [pool.submit(upload_one, task) for task in upload_tasks]
        for future in as_completed(futures):
            uploaded.append(future.result())

    print(f"Uploaded {len(uploaded):,} files total")
    return uploaded


@app.function(
    image=image,
    volumes={"/results": city_volume},
    timeout=600,
)
def download_results() -> dict[str, bytes]:
    """Download summary parquets from volume."""
    from pathlib import Path

    results_dir = Path("/results")
    files = {}
    for name in ["proto_city_populations.parquet", "city_centroids_h3_r8.parquet"]:
        path = results_dir / name
        if path.exists():
            files[name] = path.read_bytes()
            print(f"  Read {name}: {len(files[name]) / 1e6:.1f} MB")
    return files


@app.function(
    image=image,
    memory=4096,
    timeout=120,
    volumes={"/results": city_volume},
)
def list_volume_status() -> str:
    """List what's on the city volume."""
    from pathlib import Path

    results_dir = Path("/results")
    lines = []

    # Input data
    for name, path in [("cities", VOLUME_CITIES_PATH), ("geometries", VOLUME_GEOM_PATH)]:
        p = Path(path)
        if p.exists():
            lines.append(f"Input {name}: {p.stat().st_size / 1e6:.1f} MB")
        else:
            lines.append(f"Input {name}: NOT FOUND")

    # City JSON files
    json_dir = results_dir / "city_h3"
    if json_dir.exists():
        json_count = len(list(json_dir.glob("*.json")))
        lines.append(f"\nCity JSON files: {json_count:,}")
    else:
        lines.append("\nCity JSON files: 0")

    # Summary parquets
    for name in ["proto_city_populations.parquet", "city_centroids_h3_r8.parquet"]:
        path = results_dir / name
        if path.exists():
            lines.append(f"{name}: {path.stat().st_size / 1e6:.1f} MB")
        else:
            lines.append(f"{name}: NOT FOUND")

    # Batch files
    proto_batches = len(list(results_dir.glob("proto/batch_*.parquet"))) if (results_dir / "proto").exists() else 0
    centroid_batches = len(list(results_dir.glob("centroids/batch_*.parquet"))) if (results_dir / "centroids").exists() else 0
    lines.append(f"\nProto batch files: {proto_batches}")
    lines.append(f"Centroid batch files: {centroid_batches}")

    return "\n".join(lines)


# ─── Entrypoint ───────────────────────────────────────────────────────────────


@app.local_entrypoint()
def main(
    prepare: bool = False,
    upload_only: bool = False,
    download_local: bool = False,
    batch_size: int = 200,
    buffer_km: float = BUFFER_KM,
    status: bool = False,
):
    """Run the per-city H3 extraction pipeline.

    Args:
        prepare: Upload local cities.parquet + geometries_by_epoch.parquet to volume
        upload_only: Only upload existing results to R2
        download_local: Download results locally instead of R2
        batch_size: Number of cities per batch container
        buffer_km: Buffer distance around city boundaries (km)
    """
    import time
    from pathlib import Path

    print("=" * 60)
    print("Per-City H3 Extract (buffered cells + proto-city + centroids)")
    print("=" * 60)

    start_time = time.time()

    if status:
        print(list_volume_status.remote())
        return

    # ── Prepare mode: upload city data to volume ──
    if prepare:
        cities_path = Path("data/processed/cities/cities.parquet")
        geom_path = Path("data/interim/mtuc/geometries_by_epoch.parquet")

        if not cities_path.exists():
            raise FileNotFoundError(
                f"Cities not found: {cities_path}\n"
                "Run --prepare from the repo root where data/ exists."
            )
        if not geom_path.exists():
            raise FileNotFoundError(
                f"Geometries not found: {geom_path}\n"
                "Run 'uv run python -m src.cities.extract_geometries' first."
            )

        print(f"\nUploading city data to Modal volume...")
        result = upload_city_data.remote(
            cities_path.read_bytes(),
            geom_path.read_bytes(),
        )
        print(f"  {result}")
        print("Done! Now run without --prepare to process.")
        return

    if upload_only:
        uploaded = upload_to_r2.remote()
        print(f"Uploaded {len(uploaded)} files")
        return

    # ── Check city data exists on volume ──
    print("\nChecking city data on volume...")
    data_status = check_city_data.remote()
    for name, info in data_status.items():
        if info["exists"]:
            print(f"  {name}: {info['size_mb']} MB")
        else:
            print(f"  {name}: NOT FOUND")
            raise RuntimeError(
                f"City data not found on volume. Run --prepare first:\n"
                f"  cd pipeline && uv run modal run src/h3/modal_extract_city_h3.py --prepare"
            )

    # ── Get city IDs from volume ──
    print("\nLoading city IDs from volume...")
    all_city_ids = get_city_ids.remote()
    print(f"  {len(all_city_ids):,} cities")

    # Split into batches
    batches = [
        all_city_ids[i : i + batch_size]
        for i in range(0, len(all_city_ids), batch_size)
    ]
    print(f"  {len(batches)} batches of {batch_size}")

    # Process batches in parallel
    print("\nProcessing...")
    futures = [
        process_city_batch.spawn(batch, buffer_km)
        for batch in batches
    ]

    for i, future in enumerate(futures):
        result = future.get()
        print(f"  Batch {i + 1}/{len(batches)}: {result}")

    process_time = time.time() - start_time
    print(f"\nProcessing complete in {process_time:.1f}s")

    # Merge batch results
    print("\nMerging batch results...")
    merge_result = merge_batch_results.remote()
    print(f"  {merge_result}")

    # Upload/download
    if download_local:
        output_dir = Path("data/processed/cities")
        output_dir.mkdir(parents=True, exist_ok=True)
        files = download_results.remote()
        for name, content in files.items():
            path = output_dir / name
            path.write_bytes(content)
            print(f"  Saved {path}")
    else:
        print("\nUploading to R2...")
        uploaded = upload_to_r2.remote()
        print(f"  Uploaded {len(uploaded)} files")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Complete! Total time: {total_time:.1f}s ({total_time / 60:.1f} min)")
    print("=" * 60)

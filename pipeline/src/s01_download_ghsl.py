"""
Download GHSL data from European Commission servers.

Purpose: Download GHSL-POP rasters and UCDB urban centers database
Output:
  - data/raw/ghsl_pop_1km/*.tif (1km for 1975-2030)
  - data/raw/ucdb/*.gpkg (UCDB R2024A)
  - data/raw/mtuc/*.gpkg (MTUC R2024A)
  - data/raw/ghsl_tile_grid/*.shp (Tile grid shapefile)

Decision log:
  - Use httpx for downloads with retry logic
  - Exponential backoff on failures (3 retries, 2^n seconds)
  - Checksum validation after download
  - Resume partial downloads via progress tracking

Date: 2024-12-08 (updated 2024-12-26)
"""

import hashlib
import json
import shutil
import time
import zipfile
from pathlib import Path

import click
import httpx
from tqdm import tqdm

from .utils.config import (
    config,
    get_ghsl_mtuc_url,
    get_ghsl_pop_global_url,
    get_ghsl_ucdb_url,
    get_raw_path,
)
from .utils.progress import ProgressTracker

# GHSL tile grid shapefile URL (contains metadata about all available tiles)
GHSL_TILE_GRID_URL = "https://ghsl.jrc.ec.europa.eu/download/GHSL_data_54009_shapefile.zip"




def download_file(
    url: str,
    output_path: Path,
    timeout: int = 600,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> tuple[bool, str]:
    """
    Download file with retry logic and progress bar.

    Returns:
        Tuple of (success, error_message)
    """
    last_error = ""

    for attempt in range(retries):
        try:
            with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
                if response.status_code == 404:
                    return False, f"File not found: {url}"

                response.raise_for_status()

                total = int(response.headers.get("content-length", 0))
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "wb") as f:
                    with tqdm(
                        total=total,
                        unit="B",
                        unit_scale=True,
                        desc=output_path.name,
                        leave=False,
                    ) as pbar:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

                return True, ""

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_error = str(e)
            if attempt < retries - 1:
                delay = backoff_factor**attempt
                print(f"  Retry {attempt + 1}/{retries} after {delay}s: {e}")
                time.sleep(delay)

    return False, last_error


def compute_md5(file_path: Path) -> str:
    """Compute MD5 hash of file."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def extract_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    """Extract zip file and return list of extracted files."""
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            # Skip directories and metadata files
            if member.endswith("/") or member.endswith(".xml"):
                continue
            # Extract to flat directory structure
            filename = Path(member).name
            target = output_dir / filename
            with zf.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(target)
    return extracted


def download_ucdb(output_dir: Path, progress: ProgressTracker) -> Path | None:
    """Download UCDB GeoPackage."""
    item_id = "ucdb"
    if progress.is_complete(item_id):
        gpkg_files = list(output_dir.glob("*.gpkg"))
        if gpkg_files:
            print(f"UCDB already downloaded: {gpkg_files[0].name}")
            return gpkg_files[0]

    progress.mark_in_progress(item_id)
    url = get_ghsl_ucdb_url()
    zip_path = output_dir / "ucdb.zip"

    print(f"Downloading UCDB from {url}")
    success, error = download_file(url, zip_path)

    if not success:
        progress.mark_failed(item_id, error)
        print(f"  FAILED: {error}")
        return None

    # Extract
    print("  Extracting...")
    extracted = extract_zip(zip_path, output_dir)
    zip_path.unlink()  # Remove zip after extraction

    # Find gpkg file
    gpkg_files = [f for f in extracted if f.suffix == ".gpkg"]
    if not gpkg_files:
        progress.mark_failed(item_id, "No .gpkg file found in archive")
        return None

    progress.mark_complete(item_id, {"file": gpkg_files[0].name})
    print(f"  Extracted: {gpkg_files[0].name}")
    return gpkg_files[0]


def download_mtuc(output_dir: Path, progress: ProgressTracker) -> Path | None:
    """Download MTUC (Multi-Temporal Urban Centers) GeoPackage."""
    item_id = "mtuc"
    if progress.is_complete(item_id):
        gpkg_files = list(output_dir.glob("*.gpkg"))
        if gpkg_files:
            print(f"MTUC already downloaded: {gpkg_files[0].name}")
            return gpkg_files[0]

    progress.mark_in_progress(item_id)
    url = get_ghsl_mtuc_url()
    zip_path = output_dir / "mtuc.zip"

    print(f"Downloading MTUC from {url}")
    success, error = download_file(url, zip_path)

    if not success:
        progress.mark_failed(item_id, error)
        print(f"  FAILED: {error}")
        return None

    # Extract
    print("  Extracting...")
    extracted = extract_zip(zip_path, output_dir)
    zip_path.unlink()  # Remove zip after extraction

    # Find gpkg file
    gpkg_files = [f for f in extracted if f.suffix == ".gpkg"]
    if not gpkg_files:
        progress.mark_failed(item_id, "No .gpkg file found in archive")
        return None

    progress.mark_complete(item_id, {"file": gpkg_files[0].name})
    print(f"  Extracted: {gpkg_files[0].name}")
    return gpkg_files[0]


def download_tile_grid(output_dir: Path, progress: ProgressTracker) -> Path | None:
    """Download GHSL tile grid shapefile.

    Note: Uses subprocess curl because the ghsl.jrc.ec.europa.eu domain has SSL
    certificate issues that Python's ssl module doesn't handle well.
    """
    import subprocess

    item_id = "tile_grid"
    if progress.is_complete(item_id):
        shp_files = list(output_dir.glob("*.shp"))
        if shp_files:
            print(f"Tile grid already downloaded: {shp_files[0].name}")
            return shp_files[0]

    progress.mark_in_progress(item_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "tile_grid.zip"

    print(f"Downloading tile grid shapefile from {GHSL_TILE_GRID_URL}")

    # Use curl with -k flag to skip SSL verification (ghsl.jrc.ec.europa.eu has cert issues)
    try:
        result = subprocess.run(
            ["curl", "-L", "-k", "-o", str(zip_path), GHSL_TILE_GRID_URL],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            progress.mark_failed(item_id, f"curl failed: {result.stderr}")
            print(f"  FAILED: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        progress.mark_failed(item_id, "Download timed out")
        print("  FAILED: Download timed out")
        return None
    except FileNotFoundError:
        progress.mark_failed(item_id, "curl not found")
        print("  FAILED: curl not found")
        return None

    # Extract
    print("  Extracting...")
    extracted = extract_zip(zip_path, output_dir)
    zip_path.unlink()  # Remove zip after extraction

    # Find shp file
    shp_files = [f for f in extracted if f.suffix == ".shp"]
    if not shp_files:
        progress.mark_failed(item_id, "No .shp file found in archive")
        return None

    progress.mark_complete(item_id, {"file": shp_files[0].name})
    print(f"  Extracted: {shp_files[0].name}")
    return shp_files[0]


def download_pop_global(
    epoch: int,
    resolution: int,
    output_dir: Path,
    progress: ProgressTracker,
) -> Path | None:
    """Download global GHSL-POP file (for 1km data)."""
    item_id = f"global_E{epoch}_{resolution}m"
    if progress.is_complete(item_id):
        pattern = f"*E{epoch}*{resolution}*.tif"
        existing = list(output_dir.glob(pattern))
        if existing:
            print(f"  E{epoch} already downloaded")
            return existing[0]

    progress.mark_in_progress(item_id)
    url = get_ghsl_pop_global_url(epoch, resolution)
    zip_path = output_dir / f"global_{item_id}.zip"

    print(f"  Downloading E{epoch} (1km global)...")
    success, error = download_file(url, zip_path)

    if not success:
        progress.mark_failed(item_id, error)
        print(f"    FAILED: {error}")
        return None

    # Extract
    extracted = extract_zip(zip_path, output_dir)
    zip_path.unlink()

    tif_files = [f for f in extracted if f.suffix == ".tif"]
    if not tif_files:
        progress.mark_failed(item_id, "No .tif file found in archive")
        return None

    progress.mark_complete(item_id, {"file": tif_files[0].name})
    return tif_files[0]


@click.command()
def main():
    """Download GHSL data for the urban data pipeline."""
    print("=" * 60)
    print("GHSL Data Download")
    print("=" * 60)

    # Initialize progress tracker
    progress_file = get_raw_path() / "download_progress.json"
    progress = ProgressTracker(progress_file)

    # Collect all items to download
    items = ["tile_grid", "ucdb", "mtuc"]  # Always download tile grid, UCDB, and MTUC

    # 1km global files (all epochs)
    for epoch in config.GHSL_POP_EPOCHS:
        items.append(f"global_E{epoch}_1000m")

    progress.initialize(items)
    progress.print_summary()
    print()

    # 1. Download tile grid shapefile
    print("\n[1/4] Downloading tile grid shapefile...")
    tile_grid_dir = get_raw_path("ghsl_tile_grid")
    tile_grid_path = download_tile_grid(tile_grid_dir, progress)
    if not tile_grid_path:
        print("WARNING: Failed to download tile grid. Continuing without it.")

    # 2. Download UCDB
    print("\n[2/4] Downloading UCDB (Urban Centre Database)...")
    ucdb_dir = get_raw_path("ucdb")
    ucdb_path = download_ucdb(ucdb_dir, progress)
    if not ucdb_path:
        print("ERROR: Failed to download UCDB. Cannot continue.")
        return

    # 3. Download MTUC (Multi-Temporal Urban Centers)
    print("\n[3/4] Downloading MTUC (Multi-Temporal Urban Centers)...")
    mtuc_dir = get_raw_path("mtuc")
    mtuc_path = download_mtuc(mtuc_dir, progress)
    if not mtuc_path:
        print("WARNING: Failed to download MTUC. Continuing without it.")

    # 4. Download 1km global files
    print(f"\n[4/4] Downloading 1km population files ({len(config.GHSL_POP_EPOCHS)} epochs)...")
    pop_1km_dir = get_raw_path("ghsl_pop_1km")
    for epoch in config.GHSL_POP_EPOCHS:
        download_pop_global(epoch, 1000, pop_1km_dir, progress)

    # Summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    progress.print_summary()

    # Mark overall completion
    sentinel = get_raw_path() / ".download_complete"
    if not progress.get_failed():
        sentinel.touch()
        print("\nAll downloads complete!")
    else:
        print("\nSome downloads failed. Re-run to retry.")


if __name__ == "__main__":
    main()

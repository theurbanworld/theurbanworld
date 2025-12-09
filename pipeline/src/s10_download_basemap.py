"""
10 - Download Basemap

Purpose: Download the latest monthly Protomaps PMTiles build for self-hosting
Input: https://build.protomaps.com/ (monthly builds)
Output: data/processed/basemap/planet.pmtiles (~70GB)
        data/processed/basemap/metadata.json

Decision log:
  - Using httpx for downloads with Range header resume support
  - Validating with pmtiles CLI (external tool, not Python library)
  - Extracting metadata as part of download to avoid separate script
  - Monthly builds are YYYYMMDD.pmtiles format
Date: 2024-12-09
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
import httpx
from tqdm import tqdm

from .utils.config import get_processed_path

PROTOMAPS_BUILD_URL = "https://build.protomaps.com"
BASEMAP_FILENAME = "planet.pmtiles"
METADATA_FILENAME = "metadata.json"


def check_pmtiles_installed() -> bool:
    """Check if pmtiles CLI is installed."""
    return shutil.which("pmtiles") is not None


def get_latest_build_date() -> str:
    """Fetch the latest build date from Protomaps build page."""
    print("  Fetching build list from Protomaps...")

    response = httpx.get(f"{PROTOMAPS_BUILD_URL}/", follow_redirects=True, timeout=30)
    response.raise_for_status()

    # Parse HTML for YYYYMMDD.pmtiles links
    pattern = r"(\d{8})\.pmtiles"
    matches = re.findall(pattern, response.text)

    if not matches:
        raise RuntimeError(f"Could not find any builds at {PROTOMAPS_BUILD_URL}")

    # Sort descending and return latest
    latest = sorted(set(matches), reverse=True)[0]
    return latest


def validate_pmtiles(filepath: Path) -> bool:
    """Validate PMTiles file using pmtiles CLI."""
    try:
        result = subprocess.run(
            ["pmtiles", "show", str(filepath)],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_pmtiles_metadata(filepath: Path) -> dict:
    """Extract metadata from PMTiles file using pmtiles CLI."""
    result = subprocess.run(
        ["pmtiles", "show", "--json", str(filepath)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pmtiles show failed: {result.stderr}")

    metadata = json.loads(result.stdout)

    # Add file info
    stat = filepath.stat()
    metadata["file_size_bytes"] = stat.st_size
    metadata["file_size_human"] = f"{stat.st_size / (1024**3):.1f} GB"
    metadata["download_date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["file_path"] = str(filepath)

    return metadata


def download_with_resume(url: str, output_path: Path, timeout: int = 600) -> None:
    """
    Download a file with resume support using Range headers.

    If the file partially exists, continues from where it left off.
    """
    # Check existing file size for resume
    existing_size = 0
    if output_path.exists():
        existing_size = output_path.stat().st_size

    headers = {}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        print(f"  Resuming from {existing_size / (1024**3):.2f} GB...")

    # Make request with streaming
    with httpx.stream(
        "GET",
        url,
        headers=headers,
        follow_redirects=True,
        timeout=httpx.Timeout(timeout, connect=30),
    ) as response:
        # Handle resume response
        if response.status_code == 416:
            # Range not satisfiable - file is complete
            print("  File already complete.")
            return

        if existing_size > 0 and response.status_code != 206:
            # Server doesn't support resume, start over
            print("  Server doesn't support resume. Starting fresh download...")
            existing_size = 0
            output_path.unlink()
            response = httpx.stream(
                "GET",
                url,
                follow_redirects=True,
                timeout=httpx.Timeout(timeout, connect=30),
            ).__enter__()

        response.raise_for_status()

        # Get total size
        content_length = response.headers.get("content-length")
        if response.status_code == 206:
            # Partial content - parse Content-Range header
            content_range = response.headers.get("content-range", "")
            if "/" in content_range:
                total_size = int(content_range.split("/")[1])
            else:
                total_size = existing_size + int(content_length or 0)
        else:
            total_size = int(content_length) if content_length else 0

        # Open file in append mode for resume, write mode for fresh start
        mode = "ab" if existing_size > 0 else "wb"

        with open(output_path, mode) as f:
            with tqdm(
                total=total_size,
                initial=existing_size,
                unit="B",
                unit_scale=True,
                desc="  Downloading",
            ) as pbar:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):  # 1 MB chunks
                    f.write(chunk)
                    pbar.update(len(chunk))


@click.command()
@click.option("--force", is_flag=True, help="Force re-download even if file exists and is valid")
@click.option("--test-only", is_flag=True, help="Skip download, just validate existing file")
def main(force: bool = False, test_only: bool = False):
    """Download the latest Protomaps planet basemap."""
    print("=" * 60)
    print("DOWNLOAD BASEMAP")
    print("=" * 60)
    print()

    # Check dependencies
    print("[1/5] Checking dependencies...")
    if not check_pmtiles_installed():
        print("  ERROR: pmtiles CLI is required but not installed.")
        print("  Install with: go install github.com/protomaps/go-pmtiles/pmtiles@latest")
        print("  Make sure $GOPATH/bin is in your PATH.")
        sys.exit(1)
    print("  pmtiles CLI found.")

    # Set up paths
    basemap_dir = get_processed_path("basemap")
    output_file = basemap_dir / BASEMAP_FILENAME
    metadata_file = basemap_dir / METADATA_FILENAME

    # Check for existing file
    print()
    print("[2/5] Checking for existing basemap...")
    if output_file.exists():
        if test_only:
            print(f"  Found: {output_file}")
            print("  Validating...")
            if validate_pmtiles(output_file):
                print("  File is valid.")
            else:
                print("  ERROR: File is invalid or corrupt.")
                sys.exit(1)
            # Continue to metadata extraction
        elif force:
            print(f"  Found: {output_file}")
            print("  --force specified, will re-download.")
            output_file.unlink()
        elif validate_pmtiles(output_file):
            print(f"  Valid basemap exists: {output_file}")
            size_gb = output_file.stat().st_size / (1024**3)
            print(f"  Size: {size_gb:.1f} GB")
            print("  Use --force to re-download.")
            print()
            print("=" * 60)
            print("SKIPPED - basemap already exists and is valid")
            print("=" * 60)
            return
        else:
            print("  Existing file is invalid. Will re-download.")
            output_file.unlink()
    else:
        print("  No existing basemap found.")

    if not test_only:
        # Find latest build
        print()
        print("[3/5] Finding latest Protomaps build...")
        try:
            build_date = get_latest_build_date()
            print(f"  Latest build: {build_date}")
        except Exception as e:
            print(f"  ERROR: {e}")
            sys.exit(1)

        # Download
        print()
        print("[4/5] Downloading basemap...")
        download_url = f"{PROTOMAPS_BUILD_URL}/{build_date}.pmtiles"
        print(f"  URL: {download_url}")
        print(f"  Target: {output_file}")
        print()
        print("  Note: This file is ~70GB. Download will resume if interrupted.")
        print()

        try:
            download_with_resume(download_url, output_file)
        except httpx.HTTPError as e:
            print(f"  ERROR: Download failed: {e}")
            print("  Run the script again to resume.")
            sys.exit(1)

        # Verify download
        print()
        print("  Verifying download...")
        if not validate_pmtiles(output_file):
            print()
            print("=" * 60)
            print("ERROR: Downloaded file is corrupt or incomplete")
            print("=" * 60)
            print()
            print("The downloaded file failed validation.")
            print("Try running the script again to resume.")
            output_file.unlink()
            sys.exit(1)
        print("  File validated successfully.")

    # Extract metadata
    print()
    print("[5/5] Extracting metadata...")
    try:
        metadata = get_pmtiles_metadata(output_file)
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"  Saved: {metadata_file}")
    except Exception as e:
        print(f"  WARNING: Could not extract metadata: {e}")

    # Summary
    print()
    print("=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)
    print()
    print(f"  File: {output_file}")
    print(f"  Size: {output_file.stat().st_size / (1024**3):.1f} GB")
    if metadata_file.exists():
        print(f"  Metadata: {metadata_file}")


if __name__ == "__main__":
    main()

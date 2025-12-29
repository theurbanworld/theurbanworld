"""
Generate PMTiles for city boundaries.

Purpose: Convert city geometries to PMTiles format for efficient vector tile
         serving with MapLibre. Uses tippecanoe for proper zoom-level
         simplification.

Usage:
  uv run python -m src.s07_generate_boundary_pmtiles           # Generate and upload
  uv run python -m src.s07_generate_boundary_pmtiles --local   # Generate only (no upload)

Requirements:
  - tippecanoe installed (brew install tippecanoe)
  - R2 credentials in .env

Date: 2025-12-28
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import boto3
import geopandas as gpd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
GEOMETRIES_PARQUET = Path("data/interim/mtuc/geometries_by_epoch.parquet")
OUTPUT_PMTILES = Path("data/processed/tiles/city_boundaries.pmtiles")
R2_KEY = "tiles/city_boundaries.pmtiles"


def load_geometries() -> gpd.GeoDataFrame:
    """Load city geometries from parquet."""
    print(f"Loading geometries from {GEOMETRIES_PARQUET}...")
    gdf = gpd.read_parquet(GEOMETRIES_PARQUET)
    print(f"  Loaded {len(gdf):,} geometries ({gdf['city_id'].nunique():,} cities)")
    return gdf


def generate_geojson(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Convert GeoDataFrame to GeoJSON for tippecanoe."""
    print(f"Converting to GeoJSON...")

    # Keep only needed columns
    gdf_export = gdf[["city_id", "epoch", "geometry"]].copy()

    # Ensure city_id is string for tippecanoe
    gdf_export["city_id"] = gdf_export["city_id"].astype(str)
    gdf_export["epoch"] = gdf_export["epoch"].astype(int)

    # Write to GeoJSON
    gdf_export.to_file(output_path, driver="GeoJSON")
    file_size = output_path.stat().st_size / 1e6
    print(f"  Wrote {output_path} ({file_size:.1f} MB)")


def run_tippecanoe(geojson_path: Path, pmtiles_path: Path) -> None:
    """Run tippecanoe to generate PMTiles."""
    print("Running tippecanoe...")

    # Ensure output directory exists
    pmtiles_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "tippecanoe",
        "-o", str(pmtiles_path),
        "--force",  # Overwrite existing
        "--layer=city_boundaries",
        "--minimum-zoom=0",
        "--maximum-zoom=14",
        "--simplification=10",  # Simplify at lower zooms
        "--detect-shared-borders",  # Better polygon simplification
        "--coalesce-densest-as-needed",  # Handle dense areas
        "--extend-zooms-if-still-dropping",  # Ensure all features visible
        str(geojson_path),
    ]

    print(f"  Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  stderr: {result.stderr}")
        raise RuntimeError(f"tippecanoe failed: {result.stderr}")

    file_size = pmtiles_path.stat().st_size / 1e6
    print(f"  Generated {pmtiles_path} ({file_size:.1f} MB)")


def upload_to_r2(local_path: Path, r2_key: str) -> str:
    """Upload PMTiles to R2."""
    print(f"Uploading to R2...")

    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["R2_BUCKET_NAME"]

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    file_size = local_path.stat().st_size / 1e6
    print(f"  Uploading {local_path.name} ({file_size:.1f} MB) -> {r2_key}")

    s3.upload_file(
        str(local_path),
        bucket_name,
        r2_key,
        ExtraArgs={"ContentType": "application/x-protomaps-tiles+sqlite3"},
    )

    print(f"  Uploaded to s3://{bucket_name}/{r2_key}")
    return f"s3://{bucket_name}/{r2_key}"


def main(local_only: bool = False) -> None:
    """Generate city boundary PMTiles and upload to R2."""
    print("=" * 60)
    print("City Boundaries PMTiles Generator")
    print("=" * 60)

    # Load geometries
    gdf = load_geometries()

    # Use temp file for GeoJSON (large intermediate file)
    with tempfile.TemporaryDirectory() as tmpdir:
        geojson_path = Path(tmpdir) / "city_boundaries.geojson"

        # Convert to GeoJSON
        generate_geojson(gdf, geojson_path)

        # Run tippecanoe
        run_tippecanoe(geojson_path, OUTPUT_PMTILES)

    # Upload to R2
    if not local_only:
        upload_to_r2(OUTPUT_PMTILES, R2_KEY)
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_PMTILES}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate city boundary PMTiles")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

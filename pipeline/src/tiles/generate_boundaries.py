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

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import boto3
import geopandas as gpd
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
GEOMETRIES_PARQUET = Path("data/interim/mtuc/geometries_by_epoch.parquet")
OUTPUT_PMTILES = Path("data/processed/tiles/city_boundaries.pmtiles")
R2_KEY = "tiles/city_boundaries.pmtiles"

# Trend threshold: |CAGR| < 0.5% is considered stable
TREND_THRESHOLD = 0.005


def compute_trend(from_prev: Optional[float], to_next: Optional[float], threshold: float = TREND_THRESHOLD) -> int:
    """
    Compute trend indicator from prev/next growth rates.

    Returns: -1 (shrinking), 0 (stable/mixed), 1 (growing)

    Logic:
    - Both available, same sign above threshold → that sign
    - Both available, opposite signs → 0 (mixed)
    - Only one available → use that value
    - Below threshold → 0 (stable)
    """
    # Determine sign for each direction (0 if missing or below threshold)
    from_prev_sign = 0
    if from_prev is not None and not np.isnan(from_prev) and abs(from_prev) >= threshold:
        from_prev_sign = 1 if from_prev > 0 else -1

    to_next_sign = 0
    if to_next is not None and not np.isnan(to_next) and abs(to_next) >= threshold:
        to_next_sign = 1 if to_next > 0 else -1

    # Both stable/missing → stable
    if from_prev_sign == 0 and to_next_sign == 0:
        return 0
    # Only one available → use that
    if from_prev_sign == 0:
        return to_next_sign
    if to_next_sign == 0:
        return from_prev_sign
    # Both available, same sign → that sign
    if from_prev_sign == to_next_sign:
        return from_prev_sign
    # Opposite signs → mixed
    return 0


def compute_density_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Add density CAGR columns using window functions."""
    df = df.sort_values(["city_id", "epoch"]).copy()

    # Shift to get prev/next density
    df["prev_density"] = df.groupby("city_id")["density_per_km2"].shift(1)
    df["next_density"] = df.groupby("city_id")["density_per_km2"].shift(-1)

    # CAGR over 5-year epochs: (current/prev)^0.2 - 1
    # Handle division by zero and negative values
    with np.errstate(divide="ignore", invalid="ignore"):
        df["density_cagr_from_prev"] = np.where(
            (df["prev_density"] > 0) & (df["density_per_km2"] > 0),
            (df["density_per_km2"] / df["prev_density"]) ** 0.2 - 1,
            np.nan,
        )
        df["density_cagr_to_next"] = np.where(
            (df["density_per_km2"] > 0) & (df["next_density"] > 0),
            (df["next_density"] / df["density_per_km2"]) ** 0.2 - 1,
            np.nan,
        )

    return df.drop(columns=["prev_density", "next_density"])


def load_geometries() -> gpd.GeoDataFrame:
    """Load city geometries with names, populations, density, and trends."""
    print(f"Loading geometries from {GEOMETRIES_PARQUET}...")
    gdf = gpd.read_parquet(GEOMETRIES_PARQUET)
    print(f"  Loaded {len(gdf):,} geometries ({gdf['city_id'].nunique():,} cities)")

    # Load city names
    print("Loading city names...")
    cities = pd.read_parquet("data/processed/cities/cities.parquet")[["city_id", "name"]]
    print(f"  Loaded {len(cities):,} city names")

    # Load per-epoch population and density
    print("Loading per-epoch populations and density...")
    populations = pd.read_parquet("data/processed/cities/city_populations.parquet")[
        ["city_id", "epoch", "population", "density_per_km2"]
    ]
    print(f"  Loaded {len(populations):,} population records")

    # Load population growth rates from rankings
    print("Loading population growth rates...")
    rankings = pd.read_parquet("data/processed/cities/city_rankings.parquet")[
        ["city_id", "epoch", "growth_from_prev", "growth_to_next"]
    ]
    print(f"  Loaded {len(rankings):,} ranking records")

    # Merge populations with growth rates
    pop_with_growth = populations.merge(rankings, on=["city_id", "epoch"], how="left")

    # Compute density trends (CAGR of density between epochs)
    print("Computing density trends...")
    pop_with_trends = compute_density_trends(pop_with_growth)

    # Compute trend indicators
    print("Computing trend indicators...")
    pop_with_trends["pop_trend"] = pop_with_trends.apply(
        lambda row: compute_trend(row["growth_from_prev"], row["growth_to_next"]), axis=1
    )
    pop_with_trends["density_trend"] = pop_with_trends.apply(
        lambda row: compute_trend(row["density_cagr_from_prev"], row["density_cagr_to_next"]), axis=1
    )

    # Keep only needed columns for join
    pop_final = pop_with_trends[
        ["city_id", "epoch", "population", "density_per_km2", "pop_trend", "density_trend"]
    ]

    # Join name (one per city)
    gdf = gdf.merge(cities, on="city_id", how="left")
    print(f"  Joined names: {gdf['name'].notna().sum():,} matched")

    # Join population, density, and trends (per city-epoch)
    gdf = gdf.merge(pop_final, on=["city_id", "epoch"], how="left")
    print(f"  Joined populations: {gdf['population'].notna().sum():,} matched")
    print(f"  Joined density: {gdf['density_per_km2'].notna().sum():,} matched")

    return gdf


def generate_geojson(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Convert GeoDataFrame to GeoJSON for tippecanoe."""
    print("Converting to GeoJSON...")

    # Keep needed columns including name, population, density, and trends
    gdf_export = gdf[
        ["city_id", "epoch", "name", "population", "density_per_km2", "pop_trend", "density_trend", "geometry"]
    ].copy()

    # Ensure proper types for tippecanoe
    gdf_export["city_id"] = gdf_export["city_id"].astype(str)
    gdf_export["epoch"] = gdf_export["epoch"].astype(int)
    gdf_export["name"] = gdf_export["name"].fillna("")
    gdf_export["population"] = gdf_export["population"].fillna(0).astype(int)
    gdf_export["density_per_km2"] = gdf_export["density_per_km2"].fillna(0).round(1)
    gdf_export["pop_trend"] = gdf_export["pop_trend"].fillna(0).astype(int)
    gdf_export["density_trend"] = gdf_export["density_trend"].fillna(0).astype(int)

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

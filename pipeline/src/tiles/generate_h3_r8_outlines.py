"""
Generate PMTiles for dissolved H3 R8 city outlines.

Purpose: Create dissolved city outline polygons from H3 resolution 8 cells for each epoch.
         Each city-epoch gets one (multi)polygon showing the city's footprint.

Usage:
  uv run python -m src.tiles.generate_h3_r8_outlines           # Generate and upload
  uv run python -m src.tiles.generate_h3_r8_outlines --local   # Generate only

Requirements:
  - tippecanoe installed (brew install tippecanoe)
  - H3 data: data/processed/ghsl_h3_r8/h3_r8_pop_{epoch}.parquet
  - City populations: data/processed/cities/city_populations_h3_r8.parquet
  - City rankings: data/processed/cities/city_rankings_h3_r8.parquet

Date: 2026-03-01
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import polars as pl
from dotenv import load_dotenv
from shapely import Polygon
from shapely.ops import unary_union

import h3

from ..tiles.generate_boundaries import compute_density_trends, compute_trend
from ..utils.config import config, get_processed_path
from ..utils.r2_upload import upload_to_r2

# Constants
OUTPUT_PMTILES = Path("data/processed/tiles/h3_r8_outlines.pmtiles")
OUTPUT_OUTLINES_DIR = Path("data/processed/outlines")
R2_KEY = "tiles/h3_r8_outlines.pmtiles"


def h3_cell_to_polygon(h3_index_int: int) -> Polygon:
    """Convert H3 int64 index to Shapely polygon."""
    cell_str = h3.int_to_str(h3_index_int)
    boundary = h3.cell_to_boundary(cell_str)
    coords = [(lng, lat) for lat, lng in boundary]
    coords.append(coords[0])
    return Polygon(coords)


def load_outlines() -> gpd.GeoDataFrame:
    """Load H3 cells, dissolve per city-epoch, and add attributes."""
    print("Loading H3 data and city attributes...")

    # Load city names
    cities = pd.read_parquet(str(get_processed_path("cities") / "cities.parquet"))[
        ["city_id", "name"]
    ]

    # Load population data
    pop_path = get_processed_path("cities") / "city_populations_h3_r8.parquet"
    populations = pd.read_parquet(str(pop_path))[
        ["city_id", "epoch", "population", "density_per_km2"]
    ]

    # Load growth rates from rankings
    rankings_path = get_processed_path("cities") / "city_rankings_h3_r8.parquet"
    rankings = pd.read_parquet(str(rankings_path))[
        ["city_id", "epoch", "growth_from_prev", "growth_to_next"]
    ]

    # Merge and compute trends
    pop_with_growth = populations.merge(rankings, on=["city_id", "epoch"], how="left")
    pop_with_trends = compute_density_trends(pop_with_growth)
    pop_with_trends["pop_trend"] = pop_with_trends.apply(
        lambda row: compute_trend(row["growth_from_prev"], row["growth_to_next"]), axis=1
    )
    pop_with_trends["density_trend"] = pop_with_trends.apply(
        lambda row: compute_trend(row["density_cagr_from_prev"], row["density_cagr_to_next"]),
        axis=1,
    )

    input_dir = get_processed_path("ghsl_h3_r8")
    all_outlines = []

    for epoch in config.GHSL_POP_EPOCHS:
        h3_path = input_dir / f"h3_r8_pop_{epoch}.parquet"
        if not h3_path.exists():
            print(f"  Warning: {h3_path} not found, skipping")
            continue

        print(f"  Processing epoch {epoch}...")
        df = pl.read_parquet(h3_path)

        for city_id, group in df.group_by("city_id"):
            city_id = city_id[0]
            h3_indices = group["h3_index"].to_list()

            # Create hexagon polygons and dissolve
            hexagons = [h3_cell_to_polygon(idx) for idx in h3_indices]
            dissolved = unary_union(hexagons)

            all_outlines.append(
                {
                    "city_id": city_id,
                    "epoch": epoch,
                    "geometry": dissolved,
                }
            )

        print(f"    Dissolved {df['city_id'].n_unique():,} cities")

    gdf = gpd.GeoDataFrame(all_outlines, crs="EPSG:4326")

    # Join names
    gdf = gdf.merge(cities, on="city_id", how="left")

    # Join population and trend attributes
    pop_final = pop_with_trends[
        ["city_id", "epoch", "population", "density_per_km2", "pop_trend", "density_trend"]
    ]
    gdf = gdf.merge(pop_final, on=["city_id", "epoch"], how="left")

    print(f"  Total outlines: {len(gdf):,}")
    return gdf


def generate_geojson(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Convert GeoDataFrame to GeoJSON for tippecanoe."""
    print("Converting to GeoJSON...")

    gdf_export = gdf[
        [
            "city_id",
            "epoch",
            "name",
            "population",
            "density_per_km2",
            "pop_trend",
            "density_trend",
            "geometry",
        ]
    ].copy()

    gdf_export["city_id"] = gdf_export["city_id"].astype(str)
    gdf_export["epoch"] = gdf_export["epoch"].astype(int)
    gdf_export["name"] = gdf_export["name"].fillna("")
    gdf_export["population"] = gdf_export["population"].fillna(0).astype(int)
    gdf_export["density_per_km2"] = gdf_export["density_per_km2"].fillna(0).round(1)
    gdf_export["pop_trend"] = gdf_export["pop_trend"].fillna(0).astype(int)
    gdf_export["density_trend"] = gdf_export["density_trend"].fillna(0).astype(int)

    gdf_export.to_file(output_path, driver="GeoJSON")
    file_size = output_path.stat().st_size / 1e6
    print(f"  Wrote {output_path} ({file_size:.1f} MB)")


def run_tippecanoe(geojson_path: Path, pmtiles_path: Path) -> None:
    """Run tippecanoe to generate PMTiles."""
    print("Running tippecanoe...")
    pmtiles_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "tippecanoe",
        "-o",
        str(pmtiles_path),
        "--force",
        "--layer=h3_r8_outlines",
        "--minimum-zoom=0",
        "--maximum-zoom=14",
        "--simplification=10",
        "--detect-shared-borders",
        "--coalesce-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        str(geojson_path),
    ]

    print(f"  Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  stderr: {result.stderr}")
        raise RuntimeError(f"tippecanoe failed: {result.stderr}")

    file_size = pmtiles_path.stat().st_size / 1e6
    print(f"  Generated {pmtiles_path} ({file_size:.1f} MB)")


def export_city_outlines(gdf: gpd.GeoDataFrame, local_only: bool = False) -> None:
    """Export simplified city outlines as per-city JSON files for OG images.

    Filters to epoch 2025, simplifies geometries (~100m tolerance),
    and writes minimal JSON files with polygon coordinates.
    """
    print("\nExporting city outline JSON files...")

    # Filter to 2025 epoch only
    gdf_2025 = gdf[gdf["epoch"] == 2025].copy()
    print(f"  Cities in epoch 2025: {len(gdf_2025):,}")

    # Simplify geometries (0.001° ≈ 100m)
    gdf_2025["geometry"] = gdf_2025["geometry"].simplify(tolerance=0.001)

    OUTPUT_OUTLINES_DIR.mkdir(parents=True, exist_ok=True)
    exported = 0

    for _, row in gdf_2025.iterrows():
        city_id = str(row["city_id"])
        geom = row["geometry"]

        if geom is None or geom.is_empty:
            continue

        # Extract coordinates as nested lists
        # Handle both Polygon and MultiPolygon
        if geom.geom_type == "Polygon":
            coords = [list(geom.exterior.coords)]
        elif geom.geom_type == "MultiPolygon":
            coords = [list(poly.exterior.coords) for poly in geom.geoms]
        else:
            continue

        # Round coordinates to 4 decimal places (~11m precision, reduces file size)
        coords = [[[round(lon, 4), round(lat, 4)] for lon, lat in ring] for ring in coords]

        outline = {"coordinates": coords}

        local_path = OUTPUT_OUTLINES_DIR / f"{city_id}.json"
        with open(local_path, "w") as f:
            json.dump(outline, f, separators=(",", ":"))

        exported += 1

    print(f"  Exported {exported:,} city outlines to {OUTPUT_OUTLINES_DIR}")

    if not local_only:
        print("  Uploading outlines to R2 via rclone...")
        load_dotenv()

        env = os.environ.copy()
        env["RCLONE_CONFIG_R2_TYPE"] = "s3"
        env["RCLONE_CONFIG_R2_PROVIDER"] = "Cloudflare"
        env["RCLONE_CONFIG_R2_ACCESS_KEY_ID"] = os.environ["R2_ACCESS_KEY_ID"]
        env["RCLONE_CONFIG_R2_SECRET_ACCESS_KEY"] = os.environ["R2_SECRET_ACCESS_KEY"]
        env["RCLONE_CONFIG_R2_ENDPOINT"] = os.environ["R2_ENDPOINT_URL"]
        env["RCLONE_CONFIG_R2_ACL"] = "private"

        bucket = os.environ["R2_BUCKET_NAME"]
        cmd = [
            "rclone",
            "sync",
            str(OUTPUT_OUTLINES_DIR),
            f"r2:{bucket}/data/outlines",
            "--transfers=16",
            "--header-upload",
            "Content-Type: application/json",
            "--header-upload",
            "Cache-Control: public, max-age=86400",
            "--progress",
        ]

        print(f"  Running: rclone sync {OUTPUT_OUTLINES_DIR} r2:{bucket}/data/outlines")
        result = subprocess.run(cmd, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"rclone sync failed with exit code {result.returncode}")
        print(f"  Uploaded {exported:,} outline files to R2")


def main(local_only: bool = False) -> None:
    """Generate H3 R8 outline PMTiles and upload to R2."""
    print("=" * 60)
    print("H3 R8 Outlines PMTiles Generator")
    print("=" * 60)

    gdf = load_outlines()

    # Export per-city outline JSON files for OG images
    export_city_outlines(gdf, local_only=local_only)

    with tempfile.TemporaryDirectory() as tmpdir:
        geojson_path = Path(tmpdir) / "h3_r8_outlines.geojson"
        generate_geojson(gdf, geojson_path)
        run_tippecanoe(geojson_path, OUTPUT_PMTILES)

    if not local_only:
        upload_to_r2(OUTPUT_PMTILES, R2_KEY, content_type="application/x-protomaps-tiles+sqlite3")
    else:
        print("\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_PMTILES}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate H3 R8 outline PMTiles")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

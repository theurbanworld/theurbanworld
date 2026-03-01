"""
Generate PMTiles for dissolved grid-1km city outlines.

Purpose: Create dissolved city outline polygons from 1km grid pixels for each epoch.
         Each city-epoch gets one (multi)polygon showing the city's footprint.

Usage:
  uv run python -m src.tiles.generate_grid_1km_outlines           # Generate and upload
  uv run python -m src.tiles.generate_grid_1km_outlines --local   # Generate only

Requirements:
  - tippecanoe installed (brew install tippecanoe)
  - Grid data: data/processed/ghsl_grid_1km/grid_1km_pop_{epoch}.parquet
  - City populations: data/processed/cities/city_populations_grid_1km.parquet
  - City rankings: data/processed/cities/city_rankings_grid_1km.parquet

Date: 2026-03-01
"""

import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import polars as pl
from pyproj import Transformer
from shapely import box
from shapely.ops import unary_union

from ..utils.config import config, get_processed_path
from ..utils.r2_upload import upload_to_r2
from ..tiles.generate_boundaries import compute_trend, compute_density_trends

# Constants
MOLLWEIDE_CRS = "ESRI:54009"
OUTPUT_PMTILES = Path("data/processed/tiles/grid_1km_outlines.pmtiles")
R2_KEY = "tiles/grid_1km_outlines.pmtiles"

# Raster properties (from GHSL 1km Mollweide)
PIXEL_SIZE = 1000.0  # meters
RASTER_ORIGIN_X = -18041000.0
RASTER_ORIGIN_Y = 9000000.0
RASTER_WIDTH = 36082


def pixel_id_to_mollweide_box(pixel_id: int) -> tuple[float, float, float, float]:
    """Convert pixel_id to Mollweide bounding box (minx, miny, maxx, maxy)."""
    row = pixel_id // RASTER_WIDTH
    col = pixel_id % RASTER_WIDTH
    minx = RASTER_ORIGIN_X + col * PIXEL_SIZE
    maxy = RASTER_ORIGIN_Y - row * PIXEL_SIZE
    maxx = minx + PIXEL_SIZE
    miny = maxy - PIXEL_SIZE
    return (minx, miny, maxx, maxy)


def load_outlines() -> gpd.GeoDataFrame:
    """Load grid pixels, dissolve per city-epoch, and add attributes."""
    print("Loading grid data and city attributes...")

    # Load city names
    cities = pd.read_parquet(
        str(get_processed_path("cities") / "cities.parquet")
    )[["city_id", "name"]]

    # Load population data for attributes
    pop_path = get_processed_path("cities") / "city_populations_grid_1km.parquet"
    populations = pd.read_parquet(str(pop_path))[
        ["city_id", "epoch", "population", "density_per_km2"]
    ]

    # Load growth rates from rankings
    rankings_path = get_processed_path("cities") / "city_rankings_grid_1km.parquet"
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

    # Transformer for Mollweide → WGS84
    transformer = Transformer.from_crs(MOLLWEIDE_CRS, "EPSG:4326", always_xy=True)

    input_dir = get_processed_path("ghsl_grid_1km")
    all_outlines = []

    for epoch in config.GHSL_POP_EPOCHS:
        grid_path = input_dir / f"grid_1km_pop_{epoch}.parquet"
        if not grid_path.exists():
            print(f"  Warning: {grid_path} not found, skipping")
            continue

        print(f"  Processing epoch {epoch}...")
        df = pl.read_parquet(grid_path)

        # Group by city_id, dissolve pixel rectangles
        for city_id, group in df.group_by("city_id"):
            city_id = city_id[0]
            pixel_ids = group["pixel_id"].to_list()

            # Create Mollweide rectangles and dissolve
            rects = [box(*pixel_id_to_mollweide_box(pid)) for pid in pixel_ids]
            dissolved = unary_union(rects)

            # Transform to WGS84
            from shapely.ops import transform as shapely_transform
            dissolved_wgs84 = shapely_transform(transformer.transform, dissolved)

            all_outlines.append({
                "city_id": city_id,
                "epoch": epoch,
                "geometry": dissolved_wgs84,
            })

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
        ["city_id", "epoch", "name", "population", "density_per_km2", "pop_trend", "density_trend", "geometry"]
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
        "-o", str(pmtiles_path),
        "--force",
        "--layer=grid_1km_outlines",
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


def main(local_only: bool = False) -> None:
    """Generate grid 1km outline PMTiles and upload to R2."""
    print("=" * 60)
    print("Grid 1km Outlines PMTiles Generator")
    print("=" * 60)

    gdf = load_outlines()

    with tempfile.TemporaryDirectory() as tmpdir:
        geojson_path = Path(tmpdir) / "grid_1km_outlines.geojson"
        generate_geojson(gdf, geojson_path)
        run_tippecanoe(geojson_path, OUTPUT_PMTILES)

    if not local_only:
        upload_to_r2(OUTPUT_PMTILES, R2_KEY, content_type="application/x-protomaps-tiles+sqlite3")
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_PMTILES}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate grid 1km outline PMTiles")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

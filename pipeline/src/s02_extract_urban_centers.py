"""
02 - Extract urban centers from UCDB GeoPackage.

Purpose: Parse GHSL-UCDB and extract city metadata with geometries
Input: data/raw/ucdb/*.gpkg (UCDB R2024A GeoPackage)
Output:
  - data/interim/urban_centers.parquet (all 11,422 cities)
  - data/interim/urban_centers_test.parquet (6 test cities)
  - data/interim/city_geometries.gpkg (WGS84 geometries)

Decision log:
  - Extract population-weighted centroids where available
  - Reproject geometries from Mollweide to WGS84
  - Calculate bounding boxes for tile intersection
  - Use fuzzy matching for test city selection
Date: 2024-12-08
"""

import re
from pathlib import Path

import click
import geopandas as gpd
import polars as pl
from shapely import Polygon
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_raw_path
from .utils.geometry_utils import (
    fix_invalid_geometry,
    get_bounding_box,
    mollweide_to_wgs84,
)
from .utils.tile_utils import estimate_tiles_for_bbox_wgs84


def load_ucdb(gpkg_path: Path) -> gpd.GeoDataFrame:
    """
    Load UCDB GeoPackage with geometry validation.

    Returns:
        GeoDataFrame with all urban centers
    """
    print(f"Loading UCDB from {gpkg_path}...")
    gdf = gpd.read_file(gpkg_path)
    print(f"  Loaded {len(gdf)} urban centers")

    # Fix any invalid geometries
    invalid_count = (~gdf.geometry.is_valid).sum()
    if invalid_count > 0:
        print(f"  Fixing {invalid_count} invalid geometries...")
        gdf["geometry"] = gdf.geometry.apply(fix_invalid_geometry)

    return gdf


def extract_metadata(gdf: gpd.GeoDataFrame) -> pl.DataFrame:
    """
    Extract relevant metadata from UCDB.

    Maps UCDB columns to our simplified schema.
    """
    # UCDB column names vary by version - detect available columns
    col_mapping = {}

    # Try different possible column names for each field
    name_candidates = ["UC_NM_MN", "NAME", "name", "CTR_MN_NM"]
    for col in name_candidates:
        if col in gdf.columns:
            col_mapping["name"] = col
            break

    country_candidates = ["CTR_MN_ISO", "CNTR_CODE", "country_code", "ISO3"]
    for col in country_candidates:
        if col in gdf.columns:
            col_mapping["country_code"] = col
            break

    pop_candidates = ["P15", "P20", "POP_2015", "POP_2020", "population"]
    for col in pop_candidates:
        if col in gdf.columns:
            col_mapping["population"] = col
            break

    area_candidates = ["AREA", "area_km2", "B15", "B20"]
    for col in area_candidates:
        if col in gdf.columns:
            col_mapping["area"] = col
            break

    # ID column
    id_candidates = ["ID_HDC_G0", "UC_ID", "id", "FID"]
    for col in id_candidates:
        if col in gdf.columns:
            col_mapping["city_id"] = col
            break

    print(f"  Using columns: {col_mapping}")

    # Reproject to WGS84
    print("  Reprojecting to WGS84...")
    gdf_wgs84 = gdf.to_crs("EPSG:4326")

    # Extract data
    records = []
    for idx, row in tqdm(gdf_wgs84.iterrows(), total=len(gdf_wgs84), desc="  Extracting"):
        geom = row.geometry

        # Get centroid
        centroid = geom.centroid
        lat, lon = centroid.y, centroid.x

        # Get bounding box
        minx, miny, maxx, maxy = geom.bounds

        # Estimate required tiles
        tiles = estimate_tiles_for_bbox_wgs84(minx, miny, maxx, maxy)
        tile_ids = [f"R{r}_C{c}" for r, c in tiles]

        # Calculate area in km²
        # Project to equal-area CRS for accurate area calculation
        try:
            area_km2 = row.get(col_mapping.get("area"), 0)
            if area_km2 == 0 or area_km2 is None:
                # Calculate from geometry (rough estimate)
                area_km2 = geom.area * 111 * 111  # Very rough degree to km conversion
        except Exception:
            area_km2 = 0

        record = {
            "city_id": str(row.get(col_mapping.get("city_id", ""), idx)),
            "name": str(row.get(col_mapping.get("name", ""), f"City_{idx}")),
            "country_code": str(row.get(col_mapping.get("country_code", ""), "UNK")),
            "latitude": lat,
            "longitude": lon,
            "population_2020": int(row.get(col_mapping.get("population", ""), 0) or 0),
            "area_km2": float(area_km2 or 0),
            "bbox_minx": minx,
            "bbox_miny": miny,
            "bbox_maxx": maxx,
            "bbox_maxy": maxy,
            "required_tiles": tile_ids,
        }
        records.append(record)

    df = pl.DataFrame(records)
    print(f"  Extracted {len(df)} cities")
    return df


def filter_test_cities(df: pl.DataFrame, test_cities: list[str]) -> pl.DataFrame:
    """
    Filter to test cities using fuzzy matching.

    Handles variations like "New York" vs "New York City".
    """
    # Normalize names for matching
    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    test_normalized = {normalize(c): c for c in test_cities}

    matches = []
    for row in df.iter_rows(named=True):
        city_norm = normalize(row["name"])
        for test_norm, test_name in test_normalized.items():
            # Check if test city name is contained in the UCDB name
            if test_norm in city_norm or city_norm in test_norm:
                matches.append(row["city_id"])
                print(f"  Matched: {row['name']} ({row['country_code']}) -> {test_name}")
                break

    if not matches:
        print("  WARNING: No exact matches found. Using population-based selection...")
        # Fall back to top 6 by population
        top_6 = df.sort("population_2020", descending=True).head(6)
        matches = top_6["city_id"].to_list()
        for row in top_6.iter_rows(named=True):
            print(f"  Selected by population: {row['name']} ({row['population_2020']:,})")

    return df.filter(pl.col("city_id").is_in(matches))


def save_geometries(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Save geometries as GeoPackage in WGS84."""
    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    gdf_wgs84.to_file(output_path, driver="GPKG")
    print(f"  Saved geometries to {output_path}")


@click.command()
@click.option("--test-only", is_flag=True, help="Only extract test cities")
def main(test_only: bool = False):
    """Extract urban centers from UCDB."""
    print("=" * 60)
    print("Urban Centers Extraction")
    print("=" * 60)

    # Find UCDB file
    ucdb_dir = get_raw_path("ucdb")
    gpkg_files = list(ucdb_dir.glob("*.gpkg"))

    if not gpkg_files:
        print("ERROR: No UCDB GeoPackage found. Run download first.")
        return

    gpkg_path = gpkg_files[0]

    # Load UCDB
    gdf = load_ucdb(gpkg_path)

    # Extract metadata
    print("\nExtracting metadata...")
    df = extract_metadata(gdf)

    # Save full dataset
    output_dir = get_interim_path()
    full_output = output_dir / "urban_centers.parquet"
    df.write_parquet(full_output)
    print(f"\nSaved {len(df)} cities to {full_output}")

    # Save test cities
    print("\nFiltering test cities...")
    test_df = filter_test_cities(df, config.TEST_CITIES)
    test_output = output_dir / "urban_centers_test.parquet"
    test_df.write_parquet(test_output)
    print(f"Saved {len(test_df)} test cities to {test_output}")

    # Save geometries
    print("\nSaving geometries...")
    geom_output = output_dir / "city_geometries.gpkg"
    save_geometries(gdf, geom_output)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total cities: {len(df)}")
    print(f"Test cities: {len(test_df)}")
    print(f"Population range: {df['population_2020'].min():,} - {df['population_2020'].max():,}")

    # Show test cities
    print("\nTest cities:")
    for row in test_df.sort("population_2020", descending=True).iter_rows(named=True):
        print(f"  {row['name']} ({row['country_code']}): {row['population_2020']:,}")


if __name__ == "__main__":
    main()

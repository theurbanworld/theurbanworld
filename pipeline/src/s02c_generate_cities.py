"""
02b - Generate city metadata from UCDB interim files.

Purpose: Extract urban center metadata with bbox, geometry, and tile coverage
Input:
  - data/interim/ucdb/ucdb_all.parquet (merged thematic data)
  - data/interim/mtuc/centroids_2025.parquet (centroid points)
  - data/interim/mtuc/geometries_by_epoch.parquet (city geometries)
Output:
  - data/processed/cities/cities.parquet (GeoParquet with polygons)

Output Schema (cities.parquet as GeoParquet):
  | Column                   | Type      | Source                             | Notes                     |
  |--------------------------|-----------|------------------------------------|---------------------------|
  | city_id                  | str       | ID_UC_G0                           | Primary key               |
  | name                     | str       | GC_UCN_MAI_2025                    | City name                 |
  | country_name             | str       | GC_CNT_GAD_2025                    | Renamed from country_code |
  | country_code             | str       | pycountry lookup                   | ISO 3166-1 alpha-3        |
  | region                   | str       | GC_DEV_USR_2025                    | Continent/region          |
  | ucdb_year_of_birth       | int       | MTUC GC_UCB_YOB                    | First epoch city existed  |
  | geometry_2025            | Polygon   | geometries_by_epoch.parquet        | City boundary polygon     |
  | centroid_2025            | Point     | centroids_2025.parquet             | Centroid point            |
  | ucdb_population_2025     | int       | GC_POP_TOT_2025                    |                           |
  | ucdb_area_km2_2025       | float     | GC_UCA_KM2_2025                    |                           |
  | bbox_minx/miny/maxx/maxy | float     | geometries_by_epoch.parquet.bounds | From geometries.parquet   |
  | required_tiles           | list[str] | tile_utils                         | Keep existing logic       |

Decision log:
  - Separated from s02 to allow independent re-runs
  - Uses interim files instead of raw GeoPackage for faster processing
  - Converts country names to ISO 3166-1 alpha-3 codes using pycountry
  - Includes centroid point
  - Computes tile coverage for downstream GHSL processing
Date: 2024-12-11
"""

import click
import geopandas as gpd
import polars as pl
import pycountry
from tqdm import tqdm

from .utils.config import get_interim_path, get_raw_path
from .utils.tile_utils import estimate_tiles_for_bbox_wgs84


# Column mappings from UCDB to cities.parquet
UCDB_COLUMNS = {
    "ID_UC_G0": "city_id",
    "GC_UCN_MAI_2025": "name",
    "GC_CNT_GAD_2025": "country_name",
    "GC_DEV_USR_2025": "region",
    "GC_POP_TOT_2025": "ucdb_population_2025",
    "GC_UCA_KM2_2025": "ucdb_area_km2_2025",
}

# Manual country name to ISO mappings for names that pycountry doesn't recognize
COUNTRY_NAME_OVERRIDES = {
    "Democratic Republic of the Congo": "COD",
    "Northern Cyprus": "CYP",  # Use Cyprus code
    "Swaziland": "SWZ",  # Now called Eswatini
    "Turkey": "TUR",  # pycountry uses "Türkiye"
}


def country_name_to_iso3(name: str) -> str | None:
    """
    Convert country name to ISO 3166-1 alpha-3 code using pycountry.

    Args:
        name: Country name (e.g., "United States", "México")

    Returns:
        ISO 3166-1 alpha-3 code (e.g., "USA", "MEX") or None if not found
    """
    if not name:
        return None

    # Check manual overrides first
    if name in COUNTRY_NAME_OVERRIDES:
        return COUNTRY_NAME_OVERRIDES[name]

    try:
        # Try exact match first
        country = pycountry.countries.get(name=name)
        if country:
            return country.alpha_3

        # Try fuzzy search for alternate names/spellings
        results = pycountry.countries.search_fuzzy(name)
        if results:
            return results[0].alpha_3
    except LookupError:
        pass

    return None


def extract_cities(force: bool = False) -> gpd.GeoDataFrame:
    """
    Extract city metadata from UCDB interim files.

    Args:
        force: Overwrite existing output

    Returns:
        GeoDataFrame with city metadata and geometries
    """
    print("Loading interim files...")

    # Load source data
    ucdb_path = get_interim_path("ucdb") / "ucdb_all.parquet"
    geom_path = get_interim_path("mtuc") / "geometries_by_epoch.parquet"
    centroid_path = get_interim_path("mtuc") / "centroids_2025.parquet"

    for path in [ucdb_path, geom_path, centroid_path]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required file not found: {path}\n"
                "Run 'python -m src.s02_extract_ucdb extract' first."
            )

    ucdb = pl.read_parquet(ucdb_path)
    geometries = gpd.read_parquet(geom_path)
    centroids = gpd.read_parquet(centroid_path)

    print(f"  UCDB: {len(ucdb)} rows")
    print(f"  Geometries: {len(geometries)} polygons")
    print(f"  Centroids: {len(centroids)} points")

    # Select and rename columns
    print("Extracting metadata columns...")
    source_cols = list(UCDB_COLUMNS.keys())
    cities_pl = ucdb.select(source_cols).rename(UCDB_COLUMNS)

    # Convert city_id to string
    cities_pl = cities_pl.with_columns(pl.col("city_id").cast(pl.Utf8))

    # Convert population to integer (handling potential floats)
    cities_pl = cities_pl.with_columns(
        pl.col("ucdb_population_2025").cast(pl.Int64)
    )

    # Convert area to float
    cities_pl = cities_pl.with_columns(
        pl.col("ucdb_area_km2_2025").cast(pl.Float64)
    )

    # Convert to pandas for merging with geodata
    cities_df = cities_pl.to_pandas()

    # Add ISO country codes
    print("Converting country names to ISO codes...")
    country_codes = []
    failed_countries = set()

    for name in tqdm(cities_df["country_name"], desc="  Countries"):
        code = country_name_to_iso3(name)
        if code is None:
            failed_countries.add(name)
        country_codes.append(code or "UNK")

    cities_df["country_code"] = country_codes

    if failed_countries:
        print(f"  Warning: Could not resolve {len(failed_countries)} countries:")
        for name in sorted(failed_countries)[:10]:
            print(f"    - {name}")
        if len(failed_countries) > 10:
            print(f"    ... and {len(failed_countries) - 10} more")

    # Add ucdb_year_of_birth from MTUC (if available)
    print("Adding ucdb_year_of_birth from MTUC...")
    mtuc_dir = get_raw_path("mtuc")
    mtuc_files = list(mtuc_dir.glob("*.gpkg"))
    if mtuc_files:
        mtuc_gdf = gpd.read_file(mtuc_files[0])
        # Column name has trailing space in MTUC: "GC_UCB_YOB _2025"
        yob_col = [c for c in mtuc_gdf.columns if "YOB" in c]
        if yob_col:
            mtuc_yob = mtuc_gdf[["ID_MTUC_G0", yob_col[0]]].copy()
            mtuc_yob.columns = ["city_id", "ucdb_year_of_birth"]
            mtuc_yob["city_id"] = mtuc_yob["city_id"].astype(str)
            mtuc_yob["ucdb_year_of_birth"] = mtuc_yob["ucdb_year_of_birth"].astype("Int64")
            cities_df = cities_df.merge(mtuc_yob, on="city_id", how="left")
            print(f"  Added ucdb_year_of_birth for {cities_df['ucdb_year_of_birth'].notna().sum()} cities")
        else:
            print("  Warning: ucdb_year_of_birth column not found in MTUC")
            cities_df["ucdb_year_of_birth"] = None
    else:
        print("  Warning: MTUC not found, skipping ucdb_year_of_birth")
        cities_df["ucdb_year_of_birth"] = None

    # Prepare geometries with ID as string for joining
    geometries = geometries.copy()
    geometries["city_id"] = geometries["city_id"].astype(str)

    centroids = centroids.copy()
    centroids["city_id"] = centroids["city_id"].astype(str)
    centroids = centroids.rename(columns={"geometry": "centroid_2025"})

    # Merge geometry
    print("Merging with geometries...")
    cities_gdf = gpd.GeoDataFrame(
        cities_df.merge(geometries[["city_id", "geometry"]], on="city_id", how="left"),
        geometry="geometry",
        crs="EPSG:4326",
    )

    # Merge centroids
    cities_gdf = cities_gdf.merge(
        centroids[["city_id", "centroid_2025"]], on="city_id", how="left"
    )

    # Extract bounding box from geometry
    print("Extracting bounding boxes...")
    cities_gdf["bbox_minx"] = cities_gdf.geometry.apply(
        lambda g: g.bounds[0] if g else None
    )
    cities_gdf["bbox_miny"] = cities_gdf.geometry.apply(
        lambda g: g.bounds[1] if g else None
    )
    cities_gdf["bbox_maxx"] = cities_gdf.geometry.apply(
        lambda g: g.bounds[2] if g else None
    )
    cities_gdf["bbox_maxy"] = cities_gdf.geometry.apply(
        lambda g: g.bounds[3] if g else None
    )

    # Compute required tiles
    print("Computing tile coverage...")
    required_tiles = []
    for _, row in tqdm(cities_gdf.iterrows(), total=len(cities_gdf), desc="  Tiles"):
        if row.geometry:
            minx, miny, maxx, maxy = row.geometry.bounds
            tiles = estimate_tiles_for_bbox_wgs84(minx, miny, maxx, maxy)
            tile_ids = [f"R{r}_C{c}" for r, c in tiles]
        else:
            tile_ids = []
        required_tiles.append(tile_ids)

    cities_gdf["required_tiles"] = required_tiles

    # Rename geometry column to geometry_2025
    cities_gdf = cities_gdf.rename(columns={"geometry": "geometry_2025"})
    cities_gdf = cities_gdf.set_geometry("geometry_2025")

    # Reorder columns
    column_order = [
        "city_id",
        "name",
        "country_name",
        "country_code",
        "region",
        "ucdb_year_of_birth",
        "geometry_2025",
        "centroid_2025",
        "ucdb_population_2025",
        "ucdb_area_km2_2025",
        "bbox_minx",
        "bbox_miny",
        "bbox_maxx",
        "bbox_maxy",
        "required_tiles",
    ]
    cities_gdf = cities_gdf[column_order]

    return cities_gdf


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
def main(force: bool = False):
    """Extract city metadata from UCDB interim files."""
    print("=" * 60)
    print("City Metadata Extraction")
    print("=" * 60)

    # Output path
    output_path = get_interim_path() / "cities.parquet"

    # Check if output exists
    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    # Extract cities
    cities_gdf = extract_cities(force)

    # Save as GeoParquet
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cities_gdf.to_parquet(output_path)

    # Summary
    print("\n" + "=" * 60)
    print("Extraction Complete")
    print("=" * 60)
    print(f"Total cities: {len(cities_gdf)}")
    print(f"Countries: {cities_gdf['country_code'].nunique()}")
    print(f"Regions: {cities_gdf['region'].nunique()}")
    print(f"Output: {output_path}")

    # Show sample
    print("\nSample data:")
    sample_cols = ["city_id", "name", "country_name", "country_code", "region", "ucdb_population_2025"]
    print(cities_gdf[sample_cols].head(5).to_string(index=False))


if __name__ == "__main__":
    main()

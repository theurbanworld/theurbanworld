"""
02b - Extract city metadata from UCDB interim files.

Purpose: Extract urban center metadata with bbox, geometry, and tile coverage
Input:
  - data/interim/ucdb/ucdb_all.parquet (merged thematic data)
  - data/interim/ucdb/geometries.parquet (polygon boundaries)
  - data/interim/ucdb/centroids.parquet (centroid points)
Output:
  - data/interim/cities.parquet (GeoParquet with polygons)

Decision log:
  - Separated from s02 to allow independent re-runs
  - Uses interim files instead of raw GeoPackage for faster processing
  - Converts country names to ISO 3166-1 alpha-3 codes using pycountry
  - Includes both polygon geometry and centroid point
  - Computes tile coverage for downstream GHSL processing
Date: 2024-12-11
"""

import click
import geopandas as gpd
import polars as pl
import pycountry
from tqdm import tqdm

from .utils.config import get_interim_path
from .utils.tile_utils import estimate_tiles_for_bbox_wgs84


# Column mappings from UCDB to cities.parquet
UCDB_COLUMNS = {
    "ID_UC_G0": "city_id",
    "GC_UCN_MAI_2025": "name",
    "GC_CNT_GAD_2025": "country_name",
    "GC_DEV_USR_2025": "region",
    "GC_POP_TOT_2025": "population_2020",
    "GC_UCA_KM2_2025": "area_km2",
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
    geom_path = get_interim_path("ucdb") / "geometries.parquet"
    centroid_path = get_interim_path("ucdb") / "centroids.parquet"

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
        pl.col("population_2020").cast(pl.Int64)
    )

    # Convert area to float
    cities_pl = cities_pl.with_columns(
        pl.col("area_km2").cast(pl.Float64)
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

    # Prepare geometries with ID as string for joining
    geometries = geometries.copy()
    geometries["city_id"] = geometries["ID_UC_G0"].astype(str)
    geometries = geometries.drop(columns=["ID_UC_G0"])

    centroids = centroids.copy()
    centroids["city_id"] = centroids["ID_UC_G0"].astype(str)
    centroids = centroids.rename(columns={"geometry": "centroid"})
    centroids = centroids.drop(columns=["ID_UC_G0"])

    # Merge geometry
    print("Merging with geometries...")
    cities_gdf = gpd.GeoDataFrame(
        cities_df.merge(geometries[["city_id", "geometry"]], on="city_id", how="left"),
        geometry="geometry",
        crs="EPSG:4326",
    )

    # Merge centroids
    cities_gdf = cities_gdf.merge(
        centroids[["city_id", "centroid"]], on="city_id", how="left"
    )

    # Extract lat/lon from centroids
    print("Extracting coordinates and bounding boxes...")
    cities_gdf["latitude"] = cities_gdf["centroid"].apply(
        lambda p: p.y if p else None
    )
    cities_gdf["longitude"] = cities_gdf["centroid"].apply(
        lambda p: p.x if p else None
    )

    # Extract bounding box from geometry
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

    # Reorder columns
    column_order = [
        "city_id",
        "name",
        "country_name",
        "country_code",
        "region",
        "latitude",
        "longitude",
        "population_2020",
        "area_km2",
        "bbox_minx",
        "bbox_miny",
        "bbox_maxx",
        "bbox_maxy",
        "required_tiles",
        "geometry",
        "centroid",
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
    sample_cols = ["city_id", "name", "country_name", "country_code", "region", "population_2020"]
    print(cities_gdf[sample_cols].head(5).to_string(index=False))


if __name__ == "__main__":
    main()

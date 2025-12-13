"""
05 - Extract city areas as H3 cell sets.

Purpose: Define each city's spatial extent as a set of H3 cells
Input:
  - data/interim/cities.parquet
  - https://data.theurban.world/ghsl-pop-100m/h3_r9_pop_2025.parquet
Output:
  - data/processed/city_areas.parquet

Decision log:
  - Use UCDB polygon geometries for city areas, convert to H3 resolution 9 (for ~0.1 km² cells)
  - Use h3_r9_pop_2025.parquet to get population of H3 cells of city areas
  - Single output file with city_id column (simpler than 10k+ separate files)
"""

import click
import geopandas as gpd
import polars as pl
from tqdm import tqdm

from .utils.config import config
from .utils.h3_utils import polygon_to_h3_cells

H3_RESOLUTION = 9
POP_URL = "https://data.theurban.world/ghsl-pop-100m/h3_r9_pop_2025.parquet"


def process_city(city_id: str, geometry, population_lookup: dict) -> list[dict]:
    """Process a single city: convert polygon to H3 cells with population."""
    cells = polygon_to_h3_cells(geometry, H3_RESOLUTION)
    return [
        {"city_id": city_id, "h3_index": cell, "population": population_lookup.get(cell, 0.0)}
        for cell in cells
    ]


@click.command()
@click.option("--test-only", is_flag=True, help="Process test cities only")
def main(test_only: bool = False):
    """Extract city areas as H3 cell sets."""

    # Setup paths
    cities_path = config.PROJECT_ROOT / "data/interim/cities.parquet"
    output_path = config.PROJECT_ROOT / "data/processed/city_areas.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load cities
    print("Loading cities...")
    cities_gdf = gpd.read_parquet(cities_path)
    if test_only:
        cities_gdf = cities_gdf[cities_gdf["city_id"].isin([str(id) for id in config.TEST_CITY_IDS])]
    print(f"  {len(cities_gdf):,} cities to process")

    # Load population data into lookup dict
    print("Loading H3 population data...")
    pop_df = pl.read_parquet(POP_URL)
    population_lookup = dict(zip(pop_df["h3_index"].to_list(), pop_df["population"].to_list()))
    print(f"  Loaded {len(population_lookup):,} cells")

    # Process all cities
    print("\nProcessing cities...")
    all_rows = []
    for idx, row in tqdm(cities_gdf.iterrows(), total=len(cities_gdf), desc="Cities"):
        try:
            rows = process_city(row["city_id"], row.geometry, population_lookup)
            all_rows.extend(rows)
        except Exception as e:
            print(f"\n  ERROR {row['city_id']}: {e}")

    # Write single output file
    print(f"\nWriting {len(all_rows):,} rows to {output_path}...")
    df = pl.DataFrame(all_rows)
    df.write_parquet(output_path)

    print("Done!")


if __name__ == "__main__":
    main()

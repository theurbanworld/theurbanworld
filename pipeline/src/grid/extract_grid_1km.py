"""
Extract GHSL 1km raster pixels within city boundaries.

Purpose: Create grid-based population dataset by extracting GHSL-POP
         pixels that fall within MTUC city boundaries for each epoch.
Input:
  - data/raw/ghsl_pop_1km/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000_V1_0.tif
  - data/interim/mtuc/geometries_by_epoch.parquet
Output:
  - data/processed/ghsl_grid_1km/grid_1km_pop_{epoch}.parquet

Output Schema (grid_1km_pop_{epoch}.parquet):
  | Column     | Type    | Description                          |
  |------------|---------|--------------------------------------|
  | pixel_id   | Int64   | Encoded: row * ncols + col           |
  | lat        | Float64 | Pixel centroid latitude (WGS84)      |
  | lng        | Float64 | Pixel centroid longitude (WGS84)     |
  | population | Float64 | GHSL-POP value                       |
  | city_id    | String  | Assigned city (from MTUC polygon)    |

Decision log:
  - Rasters are in Mollweide (ESRI:54009), 1000m pixels = exactly 1 km²
  - City geometries reprojected WGS84 → Mollweide for rasterization
  - rasterio.features.rasterize() burns integer city labels onto raster grid
  - Pixel centroids transformed Mollweide → WGS84 for map coordinates
  - Each pixel assigned to one city (last-painted wins in rasterize; cities
    processed in ascending city_id order for determinism)
  - Only pixels with population > 0 AND city_id > 0 are kept
Date: 2026-03-01
"""

import click
import geopandas as gpd
import numpy as np
import polars as pl
import rasterio
from pyproj import Transformer
from rasterio.features import rasterize

from ..utils.config import config, get_processed_path, get_raw_path


# Mollweide CRS used by GHSL 1km rasters
MOLLWEIDE_CRS = "ESRI:54009"

# Raster file naming pattern
RASTER_TEMPLATE = "GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000_V1_0.tif"


def extract_grid_for_epoch(epoch: int) -> pl.DataFrame:
    """
    Extract grid pixels within city boundaries for a single epoch.

    Args:
        epoch: Year to process (1975, 1980, ..., 2030)

    Returns:
        DataFrame with pixel_id, lat, lng, population, city_id
    """
    # Load raster
    raw_dir = get_raw_path("ghsl_pop_1km")
    raster_path = raw_dir / RASTER_TEMPLATE.format(epoch=epoch)
    if not raster_path.exists():
        raise FileNotFoundError(f"Missing raster: {raster_path}")

    # Load city geometries for this epoch
    geom_path = config.INTERIM_DIR / "mtuc" / "geometries_by_epoch.parquet"
    gdf = gpd.read_parquet(geom_path)
    gdf = gdf[gdf["epoch"] == epoch].copy()
    print(f"    {len(gdf):,} city geometries for epoch {epoch}")

    if len(gdf) == 0:
        return pl.DataFrame(schema={
            "pixel_id": pl.Int64,
            "lat": pl.Float64,
            "lng": pl.Float64,
            "population": pl.Float64,
            "city_id": pl.Utf8,
        })

    # Reproject geometries from WGS84 to Mollweide
    gdf = gdf.set_crs("EPSG:4326")
    gdf_moll = gdf.to_crs(MOLLWEIDE_CRS)

    with rasterio.open(raster_path) as src:
        transform = src.transform
        nodata = src.nodata
        height, width = src.height, src.width

        # Build city_id → integer label mapping (0 = no city)
        # Sort by city_id for deterministic assignment
        city_ids = sorted(gdf_moll["city_id"].unique())
        city_id_to_label = {cid: i + 1 for i, cid in enumerate(city_ids)}
        label_to_city_id = {v: k for k, v in city_id_to_label.items()}

        # Create (geometry, label) pairs for rasterization
        shapes = [
            (row.geometry, city_id_to_label[row.city_id])
            for row in gdf_moll.itertuples()
            if row.geometry is not None and not row.geometry.is_empty
        ]

        print(f"    Rasterizing {len(shapes):,} city geometries onto {height}x{width} grid...")
        city_grid = rasterize(
            shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.int32,
            all_touched=False,
        )

        # Read population raster
        print(f"    Reading population raster...")
        pop_data = src.read(1)

    # Find pixels where both city_id > 0 and population > 0
    mask = (city_grid > 0) & (pop_data > 0) & (pop_data != nodata)
    rows, cols = np.where(mask)

    print(f"    {len(rows):,} pixels matched (city + population > 0)")

    if len(rows) == 0:
        return pl.DataFrame(schema={
            "pixel_id": pl.Int64,
            "lat": pl.Float64,
            "lng": pl.Float64,
            "population": pl.Float64,
            "city_id": pl.Utf8,
        })

    # Compute pixel centroids in Mollweide
    # transform maps (col, row) → (x, y) in Mollweide
    xs = transform.c + (cols + 0.5) * transform.a
    ys = transform.f + (rows + 0.5) * transform.e

    # Transform Mollweide → WGS84
    transformer = Transformer.from_crs(MOLLWEIDE_CRS, "EPSG:4326", always_xy=True)
    lngs, lats = transformer.transform(xs, ys)

    # Build output
    pixel_ids = rows.astype(np.int64) * width + cols.astype(np.int64)
    populations = pop_data[rows, cols]
    city_labels = city_grid[rows, cols]
    city_id_array = np.array([label_to_city_id[label] for label in city_labels])

    df = pl.DataFrame({
        "pixel_id": pixel_ids,
        "lat": lats,
        "lng": lngs,
        "population": populations,
        "city_id": city_id_array,
    })

    return df


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
@click.option("--epoch", "single_epoch", type=int, default=None, help="Process single epoch")
def main(force: bool = False, single_epoch: int | None = None):
    """Extract GHSL 1km grid pixels within city boundaries."""
    print("=" * 60)
    print("Grid 1km Population Extraction")
    print("=" * 60)

    output_dir = get_processed_path("ghsl_grid_1km")
    epochs = [single_epoch] if single_epoch else config.GHSL_POP_EPOCHS

    for epoch in epochs:
        output_path = output_dir / f"grid_1km_pop_{epoch}.parquet"

        if output_path.exists() and not force:
            print(f"\n  Skipping epoch {epoch} (exists). Use --force to overwrite.")
            continue

        print(f"\n  Processing epoch {epoch}...")
        df = extract_grid_for_epoch(epoch)

        output_dir.mkdir(parents=True, exist_ok=True)
        df.write_parquet(output_path)

        n_cities = df["city_id"].n_unique()
        total_pop = df["population"].sum()
        print(f"    Saved: {len(df):,} pixels, {n_cities:,} cities, total pop: {total_pop:,.0f}")
        print(f"    Output: {output_path}")

    print("\n" + "=" * 60)
    print("Extraction Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()

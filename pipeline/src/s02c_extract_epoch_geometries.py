"""
02c - Extract epoch-specific city geometries from MTUC.

Purpose: Extract urban center boundaries for each epoch (1975-2030) from the
         Multi-Temporal Urban Centers dataset, enabling accurate time-series
         analysis using the actual city footprint for each time period.

Input:
  - data/raw/mtuc/GHS_UCDB_MTUC_GLOBE_R2024A.gpkg (12 epoch layers)

Output:
  - data/interim/city_geometries_by_epoch.parquet (GeoParquet)

Output Schema:
  | Column   | Type    | Description                          |
  |----------|---------|--------------------------------------|
  | city_id  | str     | Urban center ID (links to cities)    |
  | epoch    | int     | Year (1975, 1980, ..., 2030)         |
  | geometry | Polygon | City boundary for that epoch         |
  | area_km2 | float   | Computed from geometry               |

Decision log:
  - Long format (one row per city-epoch) for storage efficiency and flexibility
  - Cities that didn't exist in an epoch are simply absent (no NULL rows)
  - Area computed in equal-area projection for accuracy
  - Geometry stored in WGS84 for compatibility with web mapping
Date: 2024-12-26
"""

import click
import geopandas as gpd
import pandas as pd
from tqdm import tqdm

from .utils.config import config, get_interim_path, get_raw_path
from .utils.geometry_utils import fix_invalid_geometry

# MTUC epoch layer template
MTUC_LAYER_TEMPLATE = "GHSL_UCDB_MTUC_{epoch}_GLOBE_R2024"

# All available epochs in MTUC
EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]


def extract_epoch_geometries(
    mtuc_path: str | None = None,
    epochs: list[int] | None = None,
) -> gpd.GeoDataFrame:
    """
    Extract epoch-specific geometries from MTUC GeoPackage.

    Args:
        mtuc_path: Path to MTUC GeoPackage (default: auto-detect in raw/mtuc)
        epochs: List of epochs to extract (default: all)

    Returns:
        GeoDataFrame with city_id, epoch, geometry, area_km2
    """
    # Find MTUC GeoPackage
    if mtuc_path is None:
        mtuc_dir = get_raw_path("mtuc")
        gpkg_files = list(mtuc_dir.glob("*.gpkg"))
        if not gpkg_files:
            raise FileNotFoundError(
                f"No GeoPackage found in {mtuc_dir}. Run s01_download_ghsl first."
            )
        mtuc_path = gpkg_files[0]

    print(f"Reading from: {mtuc_path}")

    if epochs is None:
        epochs = EPOCHS

    all_epochs_data = []

    for epoch in tqdm(epochs, desc="Extracting epochs"):
        layer_name = MTUC_LAYER_TEMPLATE.format(epoch=epoch)

        try:
            # Read epoch layer
            gdf = gpd.read_file(mtuc_path, layer=layer_name)
        except Exception as e:
            print(f"  Warning: Could not read layer {layer_name}: {e}")
            continue

        # Rename ID column
        gdf = gdf.rename(columns={"ID_UC_G0": "city_id"})
        gdf["city_id"] = gdf["city_id"].astype(str)

        # Add epoch column
        gdf["epoch"] = epoch

        # Fix invalid geometries
        invalid_count = (~gdf.geometry.is_valid).sum()
        if invalid_count > 0:
            gdf["geometry"] = gdf.geometry.apply(fix_invalid_geometry)

        # Compute area in km² using equal-area projection
        # Use Mollweide (ESRI:54009) for global equal-area
        gdf_equal_area = gdf.to_crs("ESRI:54009")
        gdf["area_km2"] = gdf_equal_area.geometry.area / 1e6  # m² to km²

        # Reproject to WGS84
        gdf = gdf.to_crs("EPSG:4326")

        # Keep only needed columns
        gdf = gdf[["city_id", "epoch", "geometry", "area_km2"]]

        all_epochs_data.append(gdf)
        print(f"  {epoch}: {len(gdf):,} cities")

    # Concatenate all epochs
    result = gpd.GeoDataFrame(
        pd.concat(all_epochs_data, ignore_index=True),
        crs="EPSG:4326",
    )

    print(f"\nTotal: {len(result):,} city-epoch combinations")
    print(f"Unique cities: {result['city_id'].nunique():,}")
    print(f"Epochs: {sorted(result['epoch'].unique())}")

    return result


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
@click.option(
    "--epochs",
    default=None,
    help="Comma-separated epochs to extract (default: all)",
)
def main(force: bool = False, epochs: str | None = None):
    """Extract epoch-specific city geometries from MTUC."""
    print("=" * 60)
    print("MTUC Epoch Geometry Extraction")
    print("=" * 60)

    # Output path
    output_path = get_interim_path() / "city_geometries_by_epoch.parquet"

    # Check if output exists
    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    # Parse epochs if specified
    epochs_list = None
    if epochs:
        epochs_list = [int(e.strip()) for e in epochs.split(",")]
        print(f"Extracting epochs: {epochs_list}")

    # Extract geometries
    result = extract_epoch_geometries(epochs=epochs_list)

    # Save as GeoParquet
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path)

    # Summary
    print("\n" + "=" * 60)
    print("Extraction Complete")
    print("=" * 60)
    print(f"Output: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1e6:.1f} MB")

    # Show sample
    print("\nSample data (2025 epoch):")
    sample = result[result["epoch"] == 2025].head(5)
    print(sample[["city_id", "epoch", "area_km2"]].to_string(index=False))


if __name__ == "__main__":
    main()

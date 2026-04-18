"""
Generate city populations JSON for frontend.

Purpose: Convert city_populations_{source}.parquet (long format) to nested JSON
         for epoch-aware population lookups in the frontend sidebar.

Includes proto-city (pre-birth) and post-city (post-death) population data,
birth/death years, and per-epoch population-weighted H3 centroids.

Usage:
  uv run python -m src.web_export.generate_city_populations --source h3-r8           # Generate and upload
  uv run python -m src.web_export.generate_city_populations --source h3-r8 --local   # Generate only

Date: 2026-02-08 (updated 2026-03-30)
"""

import json
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd
import polars as pl

from ..cities.density_outliers import identify_outlier_city_ids

VALID_SOURCES = ("h3-r8", "grid-1km")

# Supplementary data files (produced by modal_extract_city_h3.py)
PROTO_CITY_PARQUET = Path("data/processed/cities/proto_city_populations.parquet")
CENTROIDS_PARQUET = Path("data/processed/cities/city_centroids_h3_r8.parquet")
CITIES_PARQUET = Path("data/processed/cities/cities.parquet")
GEOMETRIES_PARQUET = Path("data/interim/mtuc/geometries_by_epoch.parquet")

EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]


def _source_slug(source: str) -> str:
    """Convert CLI source name to filename slug: 'h3-r8' → 'h3_r8'."""
    return source.replace("-", "_")


def load_populations(parquet_path: Path) -> pd.DataFrame:
    """Load city populations from parquet, filtering density outliers."""
    print(f"Loading populations from {parquet_path}...")
    df_pl = pl.read_parquet(parquet_path)
    n_before = df_pl["city_id"].n_unique()

    # Remove density outliers (same filter as compute_rankings)
    outlier_ids = identify_outlier_city_ids(df_pl)
    if outlier_ids:
        df_pl = df_pl.filter(~pl.col("city_id").is_in(outlier_ids))
        n_after = df_pl["city_id"].n_unique()
        print(f"  Filtered {len(outlier_ids)} density outlier cities ({n_before:,} → {n_after:,})")

    df = df_pl.to_pandas()
    print(f"  Loaded {len(df):,} records ({df['city_id'].nunique():,} cities)")
    return df


def load_supplementary_data() -> tuple[
    pd.DataFrame | None, pd.DataFrame | None, dict[str, int | None], dict[str, int | None]
]:
    """Load proto-city, centroid, birth/death year data if available.

    Returns:
        (proto_df, centroids_df, birth_years, death_years)
    """
    proto_df = None
    if PROTO_CITY_PARQUET.exists():
        proto_df = pl.read_parquet(PROTO_CITY_PARQUET).to_pandas()
        print(f"  Loaded {len(proto_df):,} proto/post-city records")

    centroids_df = None
    if CENTROIDS_PARQUET.exists():
        centroids_df = pl.read_parquet(CENTROIDS_PARQUET).to_pandas()
        print(f"  Loaded {len(centroids_df):,} centroid records")

    # Birth years from cities.parquet
    birth_years: dict[str, int | None] = {}
    death_years: dict[str, int | None] = {}

    if CITIES_PARQUET.exists():
        cities_gdf = gpd.read_parquet(CITIES_PARQUET)
        for _, row in cities_gdf.iterrows():
            cid = str(row["city_id"])
            yob = row.get("ucdb_year_of_birth")
            if yob is not None and not pd.isna(yob):
                birth_years[cid] = int(yob)

    # Death years from geometries_by_epoch.parquet
    if GEOMETRIES_PARQUET.exists():
        geom_df = gpd.read_parquet(GEOMETRIES_PARQUET)
        max_epochs = geom_df.groupby("city_id")["epoch"].max()
        for cid, max_epoch in max_epochs.items():
            if max_epoch < 2030:
                idx = EPOCHS.index(max_epoch)
                if idx + 1 < len(EPOCHS):
                    death_years[str(cid)] = EPOCHS[idx + 1]

    if birth_years:
        print(f"  Loaded {len(birth_years):,} birth years")
    if death_years:
        print(f"  Loaded {len(death_years):,} death years")

    return proto_df, centroids_df, birth_years, death_years


def generate_json(df: pd.DataFrame) -> list[dict]:
    """Pivot long-format DataFrame to nested JSON structure.

    Output structure:
      [{
        city_id: string,
        birth_year?: number,
        death_year?: number,
        epochs: {
          [year]: {
            population, area_km2, density_per_km2,
            proto?: true, post?: true,
            centroid_h3?: string
          }
        }
      }]
    """
    print("Generating nested JSON...")

    proto_df, centroids_df, birth_years, death_years = load_supplementary_data()

    # Build centroid lookup: (city_id, epoch) -> centroid_h3
    centroid_lookup: dict[tuple[str, int], str] = {}
    if centroids_df is not None:
        for _, row in centroids_df.iterrows():
            centroid_lookup[(str(row["city_id"]), int(row["epoch"]))] = str(row["centroid_h3"])

    # Build proto/post lookup: (city_id, epoch) -> {population, area_km2, ...}
    proto_lookup: dict[tuple[str, int], dict] = {}
    if proto_df is not None:
        for _, row in proto_df.iterrows():
            proto_lookup[(str(row["city_id"]), int(row["epoch"]))] = {
                "population": int(round(row["population"])),
                "area_km2": round(float(row["area_km2"]), 1),
                "density_per_km2": round(float(row["density_per_km2"]), 1),
                "state": row["state"],
            }

    cities: dict[str, dict] = defaultdict(dict)
    for _, row in df.iterrows():
        city_id = str(row["city_id"])
        epoch = str(int(row["epoch"]))
        epoch_data = {
            "population": int(round(row["population"])),
            "area_km2": round(float(row["area_km2"]), 1),
            "density_per_km2": round(float(row["density_per_km2"]), 1),
        }

        # Add centroid if available
        centroid = centroid_lookup.get((city_id, int(row["epoch"])))
        if centroid:
            epoch_data["centroid_h3"] = centroid

        cities[city_id][epoch] = epoch_data

    # Merge proto/post-city epochs (only for epochs not already in the data)
    for (city_id, epoch), proto_data in proto_lookup.items():
        epoch_str = str(epoch)
        if epoch_str not in cities.get(city_id, {}):
            epoch_entry = {
                "population": proto_data["population"],
                "area_km2": proto_data["area_km2"],
                "density_per_km2": proto_data["density_per_km2"],
            }
            if proto_data["state"] == "proto":
                epoch_entry["proto"] = True
            elif proto_data["state"] == "post":
                epoch_entry["post"] = True

            centroid = centroid_lookup.get((city_id, epoch))
            if centroid:
                epoch_entry["centroid_h3"] = centroid

            cities[city_id][epoch_str] = epoch_entry

    result = []
    for cid, epochs in cities.items():
        record: dict = {"city_id": cid, "epochs": epochs}
        if cid in birth_years:
            record["birth_year"] = birth_years[cid]
        if cid in death_years:
            record["death_year"] = death_years[cid]
        result.append(record)

    print(f"  Generated {len(result):,} city records")
    return result


def save_json(data: list[dict], output_path: Path) -> None:
    """Save to compact JSON."""
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    file_size = output_path.stat().st_size / 1e6
    print(f"  Saved {output_path} ({file_size:.1f} MB)")


def main(source: str, local_only: bool = False) -> None:
    """Generate city populations JSON and upload to R2."""
    slug = _source_slug(source)

    print("=" * 60)
    print(f"City Populations JSON Generator (source: {source})")
    print("=" * 60)

    parquet_path = Path(f"data/processed/cities/city_populations_{slug}.parquet")
    output_json = Path(f"data/processed/tiles/city_populations_{slug}.json")
    r2_key = f"data/city_populations_{slug}.json"

    df = load_populations(parquet_path)
    data = generate_json(df)
    save_json(data, output_json)

    if not local_only:
        from ..utils.r2_upload import upload_to_r2

        print()
        upload_to_r2(output_json, r2_key, content_type="application/json")
    else:
        print("\nLocal only mode - skipping R2 upload")
        print(f"Output: {output_json}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate city populations JSON")
    parser.add_argument("--source", required=True, choices=VALID_SOURCES, help="Data source")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(source=args.source, local_only=args.local)

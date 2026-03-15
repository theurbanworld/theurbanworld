"""
Generate city populations JSON for frontend.

Purpose: Convert city_populations_{source}.parquet (long format) to nested JSON
         for epoch-aware population lookups in the frontend sidebar.

Usage:
  uv run python -m src.web_export.generate_city_populations --source h3-r8           # Generate and upload
  uv run python -m src.web_export.generate_city_populations --source h3-r8 --local   # Generate only

Date: 2026-02-08
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import polars as pl

from ..cities.density_outliers import identify_outlier_city_ids

VALID_SOURCES = ("h3-r8", "grid-1km")


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


def generate_json(df: pd.DataFrame) -> list[dict]:
    """Pivot long-format DataFrame to nested JSON structure.

    Output matches the CityPopulationRecord interface in useCityPopulations.ts:
      [{ city_id: string, epochs: { [year]: { population, area_km2, density_per_km2 } } }]
    """
    print("Generating nested JSON...")

    cities: dict[str, dict] = defaultdict(dict)
    for _, row in df.iterrows():
        city_id = str(row["city_id"])
        epoch = str(int(row["epoch"]))
        cities[city_id][epoch] = {
            "population": int(round(row["population"])),
            "area_km2": round(float(row["area_km2"]), 1),
            "density_per_km2": round(float(row["density_per_km2"]), 1),
        }

    result = [
        {"city_id": cid, "epochs": epochs}
        for cid, epochs in cities.items()
    ]

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
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {output_json}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate city populations JSON")
    parser.add_argument("--source", required=True, choices=VALID_SOURCES, help="Data source")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(source=args.source, local_only=args.local)

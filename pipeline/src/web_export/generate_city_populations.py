"""
Generate city populations JSON for frontend.

Purpose: Convert city_populations.parquet (long format) to nested JSON
         for epoch-aware population lookups in the frontend sidebar.

Usage:
  uv run python -m src.s09b_generate_city_populations_json           # Generate and upload
  uv run python -m src.s09b_generate_city_populations_json --local   # Generate only (no upload)

Date: 2026-02-08
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

# Constants
POPULATIONS_PARQUET = Path("data/processed/cities/city_populations.parquet")
OUTPUT_JSON = Path("data/processed/tiles/city_populations.json")
R2_KEY = "data/city_populations.json"


def load_populations() -> pd.DataFrame:
    """Load city populations from parquet."""
    print(f"Loading populations from {POPULATIONS_PARQUET}...")
    df = pd.read_parquet(POPULATIONS_PARQUET)
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


def main(local_only: bool = False) -> None:
    """Generate city populations JSON and upload to R2."""
    print("=" * 60)
    print("City Populations JSON Generator")
    print("=" * 60)

    # Load populations
    df = load_populations()

    # Generate nested JSON
    data = generate_json(df)

    # Save locally
    save_json(data, OUTPUT_JSON)

    # Upload to R2
    if not local_only:
        from ..utils.r2_upload import upload_to_r2

        print()
        upload_to_r2(OUTPUT_JSON, R2_KEY, content_type="application/json")
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_JSON}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate city populations JSON")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

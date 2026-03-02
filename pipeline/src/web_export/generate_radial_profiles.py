"""
Generate radial profiles JSON for frontend.

Purpose: Convert radial_profiles_h3_r8.parquet to compact nested JSON
         for epoch-aware radial density profile charts in the frontend sidebar.

Output format: Record<city_id, Record<epoch, (number | null)[]>>
  Each array = density_per_km2 per ring (index = ring_index), trimmed at last non-null.

Usage:
  uv run python -m src.web_export.generate_radial_profiles           # Generate and upload
  uv run python -m src.web_export.generate_radial_profiles --local   # Generate only

Date: 2026-03-01
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


def load_profiles(parquet_path: Path) -> pd.DataFrame:
    """Load radial profiles from parquet."""
    print(f"Loading radial profiles from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"  Loaded {len(df):,} records ({df['city_id'].nunique():,} cities)")
    return df


def generate_json(df: pd.DataFrame) -> dict:
    """Convert radial profiles DataFrame to compact nested JSON.

    Output: { city_id: { epoch: [density_per_km2, ...] } }
    Arrays trimmed at last non-null value. Null/0 density stored as null.
    Values rounded to 1 decimal.
    """
    print("Generating nested JSON...")

    cities: dict[str, dict[str, list]] = defaultdict(dict)

    # Group by city_id and epoch, sort by ring_index
    for (city_id, epoch), group in df.groupby(["city_id", "epoch"]):
        group_sorted = group.sort_values("ring_index")
        densities = group_sorted["density_per_km2"].tolist()

        # Round and convert NaN/None to None
        rounded = []
        for d in densities:
            if d is None or (isinstance(d, float) and (pd.isna(d) or d == 0)):
                rounded.append(None)
            else:
                rounded.append(round(float(d), 1))

        # Trim trailing nulls
        while rounded and rounded[-1] is None:
            rounded.pop()

        if rounded:
            cities[str(city_id)][str(int(epoch))] = rounded

    print(f"  Generated {len(cities):,} city records")
    return dict(cities)


def save_json(data: dict, output_path: Path) -> None:
    """Save to compact JSON."""
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    file_size = output_path.stat().st_size / 1e6
    print(f"  Saved {output_path} ({file_size:.1f} MB)")


def main(local_only: bool = False) -> None:
    """Generate radial profiles JSON and upload to R2."""
    print("=" * 60)
    print("Radial Profiles JSON Generator")
    print("=" * 60)

    parquet_path = Path("data/processed/radial_profiles/radial_profiles_h3_r8.parquet")
    output_json = Path("data/processed/tiles/radial_profiles_h3_r8.json")
    r2_key = "data/radial_profiles_h3_r8.json"

    df = load_profiles(parquet_path)
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

    parser = argparse.ArgumentParser(description="Generate radial profiles JSON")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

"""
Generate city index JSON for frontend.

Purpose: Create a lightweight JSON file with city metadata for search,
         labels, and viewport navigation in the frontend.

Usage:
  uv run python -m src.web_export.generate_city_index           # Generate and upload
  uv run python -m src.web_export.generate_city_index --local   # Generate only (no upload)

Date: 2025-12-28
"""

import json
from pathlib import Path

import geopandas as gpd

# Constants
CITIES_PARQUET = Path("data/processed/cities/cities.parquet")
OUTPUT_JSON = Path("data/processed/tiles/cities_index.json")
R2_KEY = "data/cities_index.json"


def load_cities() -> gpd.GeoDataFrame:
    """Load cities from parquet."""
    print(f"Loading cities from {CITIES_PARQUET}...")
    gdf = gpd.read_parquet(CITIES_PARQUET)
    print(f"  Loaded {len(gdf):,} cities")
    return gdf


def generate_city_index(gdf: gpd.GeoDataFrame) -> list[dict]:
    """Generate city index list from GeoDataFrame."""
    print("Generating city index...")

    cities = []
    for _, row in gdf.iterrows():
        # Extract centroid coordinates
        centroid = row.get("centroid_2025")
        if centroid is not None and not centroid.is_empty:
            centroid_coords = [round(centroid.x, 6), round(centroid.y, 6)]
        else:
            centroid_coords = None

        # Extract bbox
        bbox = None
        if all(row.get(k) is not None for k in ["bbox_minx", "bbox_miny", "bbox_maxx", "bbox_maxy"]):
            bbox = [
                round(row["bbox_minx"], 6),
                round(row["bbox_miny"], 6),
                round(row["bbox_maxx"], 6),
                round(row["bbox_maxy"], 6),
            ]

        city = {
            "id": str(row["city_id"]),
            "name": row["name"],
            "country": row["country_name"],
            "country_code": row["country_code"],
            "centroid": centroid_coords,
            "bbox": bbox,
        }

        # Only include population if available
        pop = row.get("ucdb_population_2025")
        if pop is not None and pop > 0:
            city["population"] = int(pop)

        cities.append(city)

    # Sort by population (largest first) for search relevance
    cities.sort(key=lambda c: c.get("population", 0), reverse=True)

    print(f"  Generated index for {len(cities):,} cities")
    return cities


def save_json(cities: list[dict], output_path: Path) -> None:
    """Save city index to JSON."""
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(cities, f, separators=(",", ":"))  # Compact JSON

    file_size = output_path.stat().st_size / 1e3
    print(f"  Saved {output_path} ({file_size:.1f} KB)")


def main(local_only: bool = False) -> None:
    """Generate city index JSON and upload to R2."""
    print("=" * 60)
    print("City Index JSON Generator")
    print("=" * 60)

    # Load cities
    gdf = load_cities()

    # Generate index
    cities = generate_city_index(gdf)

    # Save locally
    save_json(cities, OUTPUT_JSON)

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

    parser = argparse.ArgumentParser(description="Generate city index JSON")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

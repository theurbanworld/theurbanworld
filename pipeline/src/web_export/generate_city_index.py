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
import polars as pl

from ..cities.density_outliers import identify_outlier_city_ids

# Constants
CITIES_PARQUET = Path("data/processed/cities/cities.parquet")
WIKIDATA_MATCHES = Path("data/processed/cities/wikidata_matches.json")
OUTPUT_JSON = Path("data/processed/tiles/cities_index.json")
R2_KEY = "data/cities_index.json"


def load_cities() -> gpd.GeoDataFrame:
    """Load cities from parquet."""
    print(f"Loading cities from {CITIES_PARQUET}...")
    gdf = gpd.read_parquet(CITIES_PARQUET)
    print(f"  Loaded {len(gdf):,} cities")
    return gdf


def load_wikidata_matches() -> dict[str, str]:
    """Load Wikidata matches if available."""
    if not WIKIDATA_MATCHES.exists():
        print("  No Wikidata matches found (run src.cities.match_wikidata first)")
        return {}
    with open(WIKIDATA_MATCHES) as f:
        matches = json.load(f)
    print(f"  Loaded {len(matches):,} Wikidata matches")
    return matches


def generate_city_index(
    gdf: gpd.GeoDataFrame, wikidata_matches: dict[str, str] | None = None
) -> list[dict]:
    """Generate city index list from GeoDataFrame."""
    print("Generating city index...")
    wikidata_matches = wikidata_matches or {}

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

        # Wikidata ID (if matched)
        city_id = str(row["city_id"])
        if city_id in wikidata_matches:
            city["wikidata_id"] = wikidata_matches[city_id]

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


def get_outlier_city_ids() -> set[str]:
    """Load population data and identify density outlier city_ids to exclude."""
    # Try H3-R8 first (primary source), fall back to grid-1km
    for slug in ("h3_r8", "grid_1km"):
        pop_path = Path(f"data/processed/cities/city_populations_{slug}.parquet")
        if pop_path.exists():
            df = pl.read_parquet(pop_path)
            outlier_ids = identify_outlier_city_ids(df)
            if outlier_ids:
                print(f"  Excluding {len(outlier_ids)} density outlier cities (from {slug})")
            return outlier_ids
    return set()


def main(local_only: bool = False) -> None:
    """Generate city index JSON and upload to R2."""
    print("=" * 60)
    print("City Index JSON Generator")
    print("=" * 60)

    # Load cities
    gdf = load_cities()

    # Filter density outliers
    outlier_ids = get_outlier_city_ids()
    if outlier_ids:
        gdf = gdf[~gdf["city_id"].isin(outlier_ids)]
        print(f"  After outlier filter: {len(gdf):,} cities")

    # Load Wikidata matches
    wikidata_matches = load_wikidata_matches()

    # Generate index
    cities = generate_city_index(gdf, wikidata_matches)

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

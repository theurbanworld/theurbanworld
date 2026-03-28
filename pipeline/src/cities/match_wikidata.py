"""
Match UCDB cities to Wikidata entities.

Purpose: Link city data to the Wikidata knowledge graph by matching on
         country code, geographic proximity, and fuzzy name similarity.

Approach:
  1. Fetch cities index from R2 (same JSON the frontend uses)
  2. Download Wikidata cities via SPARQL in paginated batches
  3. Spatial + fuzzy name join to find matches
  4. Save results as wikidata_matches.json for web export

Usage:
  uv run python -m src.cities.match_wikidata           # Full run, save + upload
  uv run python -m src.cities.match_wikidata --local    # Save locally only
  uv run python -m src.cities.match_wikidata --dry-run  # Download + match, don't save

Output:
  - data/processed/cities/wikidata_matches.json
    { "city_id": "Q1234", ... } mapping UCDB IDs to Wikidata Q-IDs

Date: 2026-03-28
"""

import argparse
import json
import math
import time
from pathlib import Path

import httpx
from rapidfuzz import fuzz

# Constants
CITIES_INDEX_URL = "https://data.theurban.world/data/cities_index.json"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
OUTPUT_PATH = Path("data/processed/cities/wikidata_matches.json")
R2_KEY = "data/wikidata_matches.json"

# Matching thresholds
DISTANCE_THRESHOLD_KM = 30
NAME_SIMILARITY_THRESHOLD = 60
HIGH_CONFIDENCE_NAME_THRESHOLD = 80

# SPARQL pagination
SPARQL_PAGE_SIZE = 5000
SPARQL_DELAY_SECONDS = 10  # Wikidata rate limits aggressively
SPARQL_MAX_RETRIES = 5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_cities_index() -> list[dict]:
    """Fetch the cities index from R2."""
    print(f"Fetching cities index from {CITIES_INDEX_URL}...")
    resp = httpx.get(CITIES_INDEX_URL, timeout=30)
    resp.raise_for_status()
    cities = resp.json()
    print(f"  Loaded {len(cities):,} cities")
    return cities


def sparql_query_page(client: httpx.Client, offset: int) -> list[dict]:
    """Fetch one page of Wikidata cities. Uses a simpler query without subclass traversal."""
    # Query cities (Q515), big cities (Q1549591), and towns (Q3957)
    # Using VALUES instead of P279* to avoid timeouts
    query = f"""
    SELECT ?city ?cityLabel ?countryCode ?lat ?lon WHERE {{
      VALUES ?type {{ wd:Q515 wd:Q1549591 wd:Q3957 wd:Q1637706 wd:Q486972 }}
      ?city wdt:P31 ?type .
      ?city wdt:P17 ?country .
      ?country wdt:P297 ?countryCode .
      ?city wdt:P625 ?coords .
      BIND(geof:latitude(?coords) AS ?lat)
      BIND(geof:longitude(?coords) AS ?lon)
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT {SPARQL_PAGE_SIZE}
    OFFSET {offset}
    """

    for attempt in range(SPARQL_MAX_RETRIES):
        try:
            resp = client.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            wait = SPARQL_DELAY_SECONDS * (2 ** attempt)
            print(f"    SPARQL error (attempt {attempt + 1}): {e}")
            print(f"    Waiting {wait}s before retry...")
            time.sleep(wait)
    else:
        print(f"    Failed after {SPARQL_MAX_RETRIES} retries at offset {offset}")
        return []

    results = []
    seen_qids = set()
    for binding in data.get("results", {}).get("bindings", []):
        entity_url = binding.get("city", {}).get("value", "")
        qid = entity_url.split("/")[-1] if entity_url else None
        if not qid or not qid.startswith("Q") or qid in seen_qids:
            continue
        seen_qids.add(qid)

        name = binding.get("cityLabel", {}).get("value", "")
        if name.startswith("Q") and name[1:].isdigit():
            continue

        lat = binding.get("lat", {}).get("value")
        lon = binding.get("lon", {}).get("value")
        country_code = binding.get("countryCode", {}).get("value", "")

        if lat and lon:
            results.append({
                "qid": qid,
                "name": name,
                "country_code": country_code,
                "lat": float(lat),
                "lon": float(lon),
            })

    return results


def fetch_all_wikidata_cities() -> list[dict]:
    """Fetch all Wikidata cities via paginated SPARQL queries."""
    print("\nFetching Wikidata cities via SPARQL...")
    all_cities: list[dict] = []
    seen_qids: set[str] = set()

    with httpx.Client(
        headers={"User-Agent": "UrbanWorldBot/1.0 (https://theurban.world; SEO linking)"}
    ) as client:
        offset = 0
        while True:
            page = sparql_query_page(client, offset)
            new_cities = [c for c in page if c["qid"] not in seen_qids]
            for c in new_cities:
                seen_qids.add(c["qid"])
            all_cities.extend(new_cities)

            print(f"  Offset {offset}: {len(page)} results, {len(new_cities)} new "
                  f"(total: {len(all_cities):,})")

            if len(page) < SPARQL_PAGE_SIZE:
                break  # Last page

            offset += SPARQL_PAGE_SIZE
            time.sleep(SPARQL_DELAY_SECONDS)

    print(f"  Total Wikidata cities: {len(all_cities):,}")
    return all_cities


def match_cities(
    ucdb_cities: list[dict], wikidata_cities: list[dict]
) -> dict[str, str]:
    """Match UCDB cities to Wikidata entities using spatial + name similarity."""
    print(f"\nMatching {len(ucdb_cities):,} UCDB cities against "
          f"{len(wikidata_cities):,} Wikidata entities...")

    # Build ISO alpha-3 to alpha-2 mapping
    import pycountry
    a3_to_a2 = {}
    for country in pycountry.countries:
        if hasattr(country, "alpha_3") and hasattr(country, "alpha_2"):
            a3_to_a2[country.alpha_3] = country.alpha_2.upper()

    # Build spatial index: grid cells of ~1 degree, keyed by (lat, lon, country_code)
    grid: dict[tuple[int, int], list[dict]] = {}
    for wd in wikidata_cities:
        key = (int(wd["lat"]), int(wd["lon"]))
        grid.setdefault(key, []).append(wd)

    matches: dict[str, str] = {}
    match_stats = {"high_confidence": 0, "spatial_name": 0, "no_match": 0}

    for city in ucdb_cities:
        centroid = city.get("centroid")
        if not centroid:
            match_stats["no_match"] += 1
            continue

        lon, lat = centroid[0], centroid[1]
        city_name = city["name"]
        city_a2 = a3_to_a2.get(city.get("country_code", ""), "")

        # Check nearby grid cells (3x3)
        cell_lat, cell_lon = int(lat), int(lon)
        candidates = []
        for dlat in range(-1, 2):
            for dlon in range(-1, 2):
                candidates.extend(grid.get((cell_lat + dlat, cell_lon + dlon), []))

        # Filter by country code first
        if city_a2:
            country_candidates = [c for c in candidates if c["country_code"] == city_a2]
            # Fall back to all candidates if no country match
            if country_candidates:
                candidates = country_candidates

        best_match = None
        best_score = 0

        for wd in candidates:
            dist = haversine_km(lat, lon, wd["lat"], wd["lon"])
            if dist > DISTANCE_THRESHOLD_KM:
                continue

            name_score = fuzz.ratio(city_name.lower(), wd["name"].lower())
            combined_score = name_score - (dist / DISTANCE_THRESHOLD_KM) * 10

            if combined_score > best_score and name_score >= NAME_SIMILARITY_THRESHOLD:
                best_score = combined_score
                best_match = wd

        if best_match:
            matches[city["id"]] = best_match["qid"]
            if best_score >= HIGH_CONFIDENCE_NAME_THRESHOLD:
                match_stats["high_confidence"] += 1
            else:
                match_stats["spatial_name"] += 1
        else:
            match_stats["no_match"] += 1

    print(f"  Matched: {len(matches):,} cities")
    print(f"    High confidence: {match_stats['high_confidence']:,}")
    print(f"    Spatial + name:  {match_stats['spatial_name']:,}")
    print(f"    No match:        {match_stats['no_match']:,}")

    return matches


def save_matches(matches: dict[str, str], output_path: Path) -> None:
    """Save matches to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(matches, f, separators=(",", ":"), sort_keys=True)

    size_kb = output_path.stat().st_size / 1024
    print(f"\nSaved {len(matches):,} matches to {output_path} ({size_kb:.1f} KB)")


def main(local_only: bool = False, dry_run: bool = False) -> None:
    """Match UCDB cities to Wikidata entities."""
    print("=" * 60)
    print("Wikidata City Matching")
    print("=" * 60)

    # Fetch cities from R2
    ucdb_cities = fetch_cities_index()

    # Fetch Wikidata cities via SPARQL
    wikidata_cities = fetch_all_wikidata_cities()

    # Spatial + name matching
    matches = match_cities(ucdb_cities, wikidata_cities)

    # Spot-check well-known cities
    spot_checks = {
        "Tokyo": "Q1490",
        "Paris": "Q90",
        "London": "Q84",
        "New York": "Q60",
        "Beijing": "Q956",
    }
    print("\nSpot check:")
    for city_name, expected_qid in spot_checks.items():
        city = next((c for c in ucdb_cities if c["name"] == city_name), None)
        if city:
            actual = matches.get(city["id"], "NOT MATCHED")
            status = "✓" if actual == expected_qid else f"✗ (got {actual})"
            print(f"  {city_name}: {status}")

    if dry_run:
        print("\nDry run — not saving.")
        return

    # Save results
    save_matches(matches, OUTPUT_PATH)

    # Upload to R2
    if not local_only:
        from ..utils.r2_upload import upload_to_r2

        print()
        upload_to_r2(OUTPUT_PATH, R2_KEY, content_type="application/json")
    else:
        print(f"\nLocal only — skipping R2 upload")

    print("\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match UCDB cities to Wikidata")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    parser.add_argument("--dry-run", action="store_true", help="Don't save results")
    args = parser.parse_args()

    main(local_only=args.local, dry_run=args.dry_run)

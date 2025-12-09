"""
08 - Compute contextual ranking metrics for cities.

Purpose: Enrich city JSONs with global/continental/national rankings, growth metrics, and density peers
Input:
  - data/processed/cities/{city_id}.json (from s07)
  - data/processed/city_index.json (for global city list)
Output:
  - data/processed/cities/{city_id}.json (enriched with context field)

Decision log:
  - Use pycountry-convert for country-to-continent mapping
  - Use DuckDB for efficient window function rankings
  - Density peers selected by population similarity and density diversity
  - World population baseline from GHSL Table 20 (UN WPP 2022 calibrated)
  - CAGR calculation uses standard compound growth formula over 45 years (1975-2020)
Date: 2024-12-09
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import click
import duckdb
import polars as pl
import pycountry
from pycountry_convert import country_alpha2_to_continent_code
from tqdm import tqdm

from .utils.config import get_processed_path
from .utils.progress import ProgressTracker

# =============================================================================
# Constants
# =============================================================================

# GHSL Table 20 - UN WPP 2022 calibrated world population
# Source: GHSL Data Package 2023
# These are TOTAL world population, not just urban centers
WORLD_POPULATION = {
    1975: 4_069_437_259,
    1980: 4_444_007_748,
    1985: 4_861_730_652,
    1990: 5_316_175_909,
    1995: 5_743_219_510,
    2000: 6_148_899_024,
    2005: 6_558_176_175,
    2010: 6_985_603_172,
    2015: 7_426_597_609,
    2020: 7_840_952_947,
}

# Continent code to name mapping
CONTINENT_NAMES = {
    "AF": "Africa",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "North America",
    "OC": "Oceania",
    "SA": "South America",
}

# Growth regime thresholds (annual percentage)
GROWTH_THRESHOLDS = {
    "explosive": 3.0,  # >= 3%
    "growing": 1.0,  # 1-3%
    "stable": 0.0,  # 0-1%
    # shrinking: < 0%
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_continent(country_code: str) -> str | None:
    """
    Map ISO 3166-1 alpha-3 country code to continent name.

    Args:
        country_code: ISO 3166-1 alpha-3 country code (e.g., "USA", "IND")

    Returns:
        Continent name or None if mapping fails
    """
    if not country_code:
        return None

    try:
        # Convert alpha-3 to alpha-2 using pycountry
        country = pycountry.countries.get(alpha_3=country_code)
        if not country:
            # Try alpha-2 directly
            country = pycountry.countries.get(alpha_2=country_code)
        if not country:
            return None

        alpha2 = country.alpha_2
        continent_code = country_alpha2_to_continent_code(alpha2)
        return CONTINENT_NAMES.get(continent_code)
    except (KeyError, AttributeError):
        return None


def calculate_cagr(start_value: float, end_value: float, years: int) -> float | None:
    """
    Calculate Compound Annual Growth Rate.

    Formula: CAGR = (end_value / start_value)^(1/years) - 1

    Args:
        start_value: Population at start year
        end_value: Population at end year
        years: Number of years between measurements

    Returns:
        CAGR as decimal (e.g., 0.025 for 2.5%) or None if invalid
    """
    if start_value is None or end_value is None:
        return None
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    return (end_value / start_value) ** (1 / years) - 1


def classify_growth_regime(annual_rate: float | None) -> str | None:
    """
    Classify growth rate into regime category.

    Args:
        annual_rate: Annual growth rate as decimal (e.g., 0.025 for 2.5%)

    Returns:
        Growth regime string or None if rate is None
    """
    if annual_rate is None:
        return None

    rate_pct = annual_rate * 100
    if rate_pct >= GROWTH_THRESHOLDS["explosive"]:
        return "explosive"
    elif rate_pct >= GROWTH_THRESHOLDS["growing"]:
        return "growing"
    elif rate_pct >= GROWTH_THRESHOLDS["stable"]:
        return "stable"
    else:
        return "shrinking"


def get_world_baseline_growth() -> float:
    """Calculate world population CAGR 1975-2020 from GHSL Table 20."""
    return calculate_cagr(WORLD_POPULATION[1975], WORLD_POPULATION[2020], 45)


def extract_time_series_endpoints(time_series: list[dict]) -> tuple[int | None, int | None]:
    """
    Extract 1975 and 2020 population from time series.

    Args:
        time_series: List of {year, population} dicts

    Returns:
        Tuple of (pop_1975, pop_2020) or (None, None) if not found
    """
    pop_1975 = None
    pop_2020 = None

    for entry in time_series:
        year = entry.get("year")
        pop = entry.get("population")
        if year == 1975:
            pop_1975 = pop
        elif year == 2020:
            pop_2020 = pop

    return pop_1975, pop_2020


def find_density_peers(
    target_city: dict,
    all_cities: list[dict],
    population_tolerance: float = 0.20,
    max_peers: int = 5,
) -> list[dict]:
    """
    Find cities with similar population but diverse densities.

    Algorithm:
    1. Filter to cities within +/-20% population
    2. Sort by density
    3. Select diverse sample from quintile positions

    Args:
        target_city: The city to find peers for
        all_cities: All cities to search
        population_tolerance: Fraction tolerance (0.20 = +/-20%)
        max_peers: Maximum number of peers to return

    Returns:
        List of peer dictionaries with density_ratio
    """
    target_pop = target_city.get("population_2020", 0)
    target_density = target_city.get("statistics", {}).get("density_avg", 0)
    target_id = target_city.get("id")

    if target_pop <= 0 or target_density <= 0:
        return []

    min_pop = target_pop * (1 - population_tolerance)
    max_pop = target_pop * (1 + population_tolerance)

    # Filter candidates
    candidates = []
    for city in all_cities:
        city_id = city.get("id")
        if city_id == target_id:
            continue

        city_pop = city.get("population_2020", 0)
        city_density = city.get("statistics", {}).get("density_avg", 0)

        if min_pop <= city_pop <= max_pop and city_density > 0:
            candidates.append(
                {
                    "city_id": city_id,
                    "name": city.get("name", ""),
                    "population": city_pop,
                    "density": round(city_density, 1),
                }
            )

    if not candidates:
        return []

    # Sort by density
    candidates.sort(key=lambda x: x["density"])

    # Select diverse sample using quintile positions
    n = len(candidates)
    if n <= max_peers:
        selected = candidates
    else:
        # Pick from quintile positions: 0%, 25%, 50%, 75%, 100%
        indices = [0, n // 4, n // 2, 3 * n // 4, n - 1]
        # Remove duplicates while preserving order
        seen = set()
        unique_indices = []
        for i in indices:
            if i not in seen:
                seen.add(i)
                unique_indices.append(i)
        selected = [candidates[i] for i in unique_indices[:max_peers]]

    # Add density ratio
    peers = []
    for peer in selected:
        peer["density_ratio"] = round(peer["density"] / target_density, 2)
        peers.append(peer)

    return peers


# =============================================================================
# Data Loading
# =============================================================================


def load_all_cities(cities_dir: Path) -> list[dict]:
    """
    Load all city JSON files into memory.

    Args:
        cities_dir: Directory containing city JSON files

    Returns:
        List of city dictionaries with parsed JSON data
    """
    cities = []
    json_files = sorted(cities_dir.glob("*.json"))

    for json_path in tqdm(json_files, desc="Loading cities"):
        # Skip index and progress files
        if json_path.name.startswith("_") or json_path.name == "city_index.json":
            continue
        try:
            city = json.loads(json_path.read_text())
            cities.append(city)
        except json.JSONDecodeError:
            continue

    return cities


def cities_to_dataframe(cities: list[dict]) -> pl.DataFrame:
    """
    Convert city list to Polars DataFrame for DuckDB processing.

    Extracts: city_id, country, population_2020, density_avg
    Adds: continent (derived from country)
    """
    records = []
    for city in cities:
        country_code = city.get("country", "")
        continent = get_continent(country_code)

        records.append(
            {
                "city_id": city.get("id", ""),
                "name": city.get("name", ""),
                "country": country_code,
                "continent": continent,
                "population_2020": city.get("population_2020", 0),
                "density_avg": city.get("statistics", {}).get("density_avg", 0),
            }
        )

    return pl.DataFrame(records)


# =============================================================================
# Ranking Computation
# =============================================================================


def compute_rankings(df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute global, continental, and national rankings using DuckDB.

    Uses window functions for efficient O(n log n) ranking.

    Args:
        df: Polars DataFrame with city data

    Returns:
        DataFrame with ranking columns added
    """
    conn = duckdb.connect()
    conn.register("cities", df)

    query = """
    SELECT
        city_id,
        name,
        country,
        continent,
        population_2020,
        density_avg,

        -- Global population rankings
        RANK() OVER (ORDER BY population_2020 DESC) as global_rank,
        PERCENT_RANK() OVER (ORDER BY population_2020) * 100 as global_percentile,

        -- Global density rankings
        RANK() OVER (ORDER BY density_avg DESC) as global_density_rank,
        PERCENT_RANK() OVER (ORDER BY density_avg) * 100 as global_density_percentile,

        -- National rankings
        RANK() OVER (PARTITION BY country ORDER BY population_2020 DESC) as national_rank,
        PERCENT_RANK() OVER (PARTITION BY country ORDER BY population_2020) * 100 as national_percentile,
        SUM(population_2020) OVER (PARTITION BY country) as country_total,
        COUNT(*) OVER (PARTITION BY country) as country_count,

        -- Continental rankings (NULL for cities without continent mapping)
        CASE WHEN continent IS NOT NULL THEN
            RANK() OVER (PARTITION BY continent ORDER BY population_2020 DESC)
        END as continental_rank,
        CASE WHEN continent IS NOT NULL THEN
            PERCENT_RANK() OVER (PARTITION BY continent ORDER BY population_2020) * 100
        END as continental_percentile,
        SUM(population_2020) OVER (PARTITION BY continent) as continent_total,
        COUNT(*) OVER (PARTITION BY continent) as continent_count,

        -- Global totals
        SUM(population_2020) OVER () as cities_total,
        COUNT(*) OVER () as total_cities

    FROM cities
    """

    result = conn.execute(query).pl()
    conn.close()

    return result


# =============================================================================
# Context Building
# =============================================================================


def build_context(
    city: dict,
    rankings: dict,
    all_cities: list[dict],
    world_baseline: float,
) -> dict:
    """
    Build complete context object for a city.

    Args:
        city: Original city JSON
        rankings: Pre-computed ranking data from DuckDB
        all_cities: All cities for peer finding
        world_baseline: World population CAGR for comparison

    Returns:
        Context dictionary to add to city JSON
    """
    population_2020 = city.get("population_2020", 0)
    time_series = city.get("time_series", [])

    # Extract time series endpoints for growth calculation
    pop_1975, pop_2020_ts = extract_time_series_endpoints(time_series)
    pop_2020 = pop_2020_ts or population_2020

    # Growth metrics
    annual_growth = calculate_cagr(pop_1975, pop_2020, 45)
    growth_regime = classify_growth_regime(annual_growth)

    relative_acceleration = None
    if annual_growth is not None:
        relative_acceleration = round((annual_growth - world_baseline) * 100, 2)

    # Find density peers
    peers = find_density_peers(city, all_cities)

    # Build global context
    global_context = {
        "rank": int(rankings["global_rank"]),
        "percentile": round(100 - rankings["global_percentile"], 1),
        "share_of_world": round(population_2020 / WORLD_POPULATION[2020], 6),
        "total_cities": int(rankings["total_cities"]),
        "density_rank": int(rankings["global_density_rank"]),
        "density_percentile": round(100 - rankings["global_density_percentile"], 1),
    }

    # Build national context
    country_count = int(rankings["country_count"])
    national_context = {
        "country": rankings["country"],
        "rank": int(rankings["national_rank"]),
        "percentile": round(100 - rankings["national_percentile"], 1) if country_count > 1 else 100.0,
        "share_of_country": round(population_2020 / rankings["country_total"], 4)
        if rankings["country_total"] > 0
        else 1.0,
        "total_cities": country_count,
    }

    # Build continental context (may be None)
    continental_context = None
    if rankings["continent"] is not None:
        continent_count = int(rankings["continent_count"])
        continental_context = {
            "continent": rankings["continent"],
            "rank": int(rankings["continental_rank"]),
            "percentile": round(100 - rankings["continental_percentile"], 1)
            if continent_count > 1
            else 100.0,
            "share_of_continent": round(population_2020 / rankings["continent_total"], 4)
            if rankings["continent_total"] > 0
            else 1.0,
            "total_cities": continent_count,
        }

    # Build growth context
    growth_context = {
        "annual_growth_rate": round(annual_growth * 100, 2) if annual_growth is not None else None,
        "world_baseline": round(world_baseline * 100, 2),
        "relative_acceleration": relative_acceleration,
        "growth_regime": growth_regime,
    }

    return {
        "global": global_context,
        "continental": continental_context,
        "national": national_context,
        "growth": growth_context,
        "density_peers": peers,
    }


# =============================================================================
# Main
# =============================================================================


@click.command()
@click.option("--test-only", is_flag=True, help="Process only test cities")
def main(test_only: bool = False):
    """Compute context metrics for city JSONs."""
    print("=" * 60)
    print("Context Metrics Computation")
    print("=" * 60)

    # Paths
    cities_dir = get_processed_path("cities")

    if not cities_dir.exists():
        print(f"ERROR: Cities directory not found: {cities_dir}")
        print("Run s07_export_web_formats first.")
        return

    # Load all cities
    print("\nLoading city data...")
    all_cities = load_all_cities(cities_dir)
    print(f"  Loaded {len(all_cities)} cities")

    if not all_cities:
        print("ERROR: No city files found")
        return

    # Filter for test mode
    if test_only:
        from .utils.config import config

        test_names = set(config.TEST_CITIES)
        all_cities = [c for c in all_cities if c.get("name") in test_names]
        print(f"  Filtered to {len(all_cities)} test cities")

    # Convert to DataFrame and compute rankings
    print("\nPreparing data...")
    df = cities_to_dataframe(all_cities)

    print("\nComputing rankings...")
    ranked_df = compute_rankings(df)

    # Convert rankings to lookup dict
    rankings_lookup = {row["city_id"]: row for row in ranked_df.to_dicts()}

    # Calculate world baseline growth
    world_baseline = get_world_baseline_growth()
    print(f"  World baseline growth (1975-2020): {world_baseline * 100:.2f}%")

    # Initialize progress tracking
    progress_file = cities_dir / "_context_progress.json"
    progress = ProgressTracker(progress_file)

    city_ids = [c.get("id") for c in all_cities]
    progress.initialize(city_ids)

    # Statistics tracking
    stats = {
        "processed": 0,
        "growth_computed": 0,
        "continental_mapped": 0,
        "peers_found": 0,
        "regimes": {"explosive": 0, "growing": 0, "stable": 0, "shrinking": 0, "unknown": 0},
    }

    # Process each city
    print(f"\nEnriching {len(all_cities)} cities...")

    for city in tqdm(all_cities, desc="Cities"):
        city_id = city.get("id")

        if progress.is_complete(city_id):
            continue

        progress.mark_in_progress(city_id)

        try:
            # Get rankings for this city
            rankings = rankings_lookup.get(city_id)

            if not rankings:
                progress.mark_failed(city_id, "No ranking data found")
                continue

            # Build context
            context = build_context(city, rankings, all_cities, world_baseline)

            # Add context to city JSON
            city["context"] = context

            # Update metadata timestamp
            if "metadata" not in city:
                city["metadata"] = {}
            city["metadata"]["context_computed_at"] = datetime.now(timezone.utc).isoformat()

            # Save updated JSON
            output_path = cities_dir / f"{city_id}.json"
            output_path.write_text(json.dumps(city, indent=2))

            # Track stats
            stats["processed"] += 1
            if context["growth"]["annual_growth_rate"] is not None:
                stats["growth_computed"] += 1
            if context["continental"] is not None:
                stats["continental_mapped"] += 1
            if context["density_peers"]:
                stats["peers_found"] += 1

            regime = context["growth"]["growth_regime"]
            if regime:
                stats["regimes"][regime] += 1
            else:
                stats["regimes"]["unknown"] += 1

            progress.mark_complete(
                city_id,
                {
                    "global_rank": context["global"]["rank"],
                    "growth_regime": regime,
                    "peers_count": len(context["density_peers"]),
                },
            )

        except Exception as e:
            progress.mark_failed(city_id, str(e))
            print(f"\n  ERROR on {city_id}: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    progress.print_summary()

    print(f"\nComputed context for {stats['processed']} cities")

    # Top 10 by population
    top_pop = ranked_df.sort("global_rank").head(10)
    print("\nTop 10 by population:")
    for row in top_pop.to_dicts():
        print(f"  {row['global_rank']:3d}. {row['name']} ({row['country']}): {row['population_2020']:,}")

    # Top 10 by density
    top_density = ranked_df.sort("global_density_rank").head(10)
    print("\nTop 10 by density:")
    for row in top_density.to_dicts():
        print(
            f"  {row['global_density_rank']:3d}. {row['name']} ({row['country']}): {row['density_avg']:,.0f}/km\u00b2"
        )

    # Growth regimes
    print("\nGrowth regimes:")
    print(
        f"  explosive: {stats['regimes']['explosive']:,} | "
        f"growing: {stats['regimes']['growing']:,} | "
        f"stable: {stats['regimes']['stable']:,} | "
        f"shrinking: {stats['regimes']['shrinking']:,}"
    )

    # Coverage stats
    total = stats["processed"]
    if total > 0:
        print("\nCoverage:")
        print(f"  Cities with continental data: {stats['continental_mapped']:,} ({100*stats['continental_mapped']/total:.1f}%)")
        print(f"  Cities with growth data: {stats['growth_computed']:,} ({100*stats['growth_computed']/total:.1f}%)")
        print(f"  Cities with density peers: {stats['peers_found']:,} ({100*stats['peers_found']/total:.1f}%)")


if __name__ == "__main__":
    main()

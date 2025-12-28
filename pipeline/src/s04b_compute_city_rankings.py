"""
Compute city rankings per epoch and growth metrics.

Purpose: Compute global/continental/national rankings for each city at each epoch,
         plus full-period growth metrics and density peer comparisons.

Input:
  - data/processed/cities/cities.parquet (city_id, country_code)
  - data/processed/cities/city_populations.parquet (city_id, epoch, population, area_km2, density_per_km2)

Output:
  - data/processed/cities/city_rankings.parquet - per-epoch rankings
  - data/processed/cities/city_growth.parquet - full-period growth metrics
  - data/processed/cities/city_density_peers.parquet - density peer relationships

Decision log:
  - Rankings computed per epoch using DuckDB window functions with PARTITION BY epoch
  - Growth rates are 5-year CAGRs between adjacent epochs
  - Full-period growth uses 55-year CAGR (1975-2030)
  - Density peers computed at 2030 only
  - World population baseline from GHSL Table 20 (UN WPP 2022 calibrated)
Date: 2025-12-27
"""

import click
import duckdb
import polars as pl
import pycountry
from pycountry_convert import country_alpha2_to_continent_code

from .utils.config import get_processed_path

# =============================================================================
# Constants
# =============================================================================

# GHSL Table 20 - UN WPP 2022 calibrated world population
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
    2025: 8_191_988_536,
    2030: 8_546_141_407,
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


# =============================================================================
# Data Loading
# =============================================================================


def load_data() -> pl.DataFrame:
    """
    Load cities and populations, join and add continent.

    Returns:
        DataFrame with city_id, epoch, population, area_km2, density_per_km2,
        cell_count, country_code, continent
    """
    cities_path = get_processed_path("cities") / "cities.parquet"
    populations_path = get_processed_path("cities") / "city_populations.parquet"

    # Load both files - deduplicate cities by city_id (take first occurrence)
    cities = (
        pl.read_parquet(cities_path)
        .select(["city_id", "name", "country_code"])
        .unique(subset=["city_id"], keep="first")
    )
    populations = pl.read_parquet(populations_path)

    # Add continent to cities
    cities = cities.with_columns(
        pl.col("country_code")
        .map_elements(get_continent, return_dtype=pl.String)
        .alias("continent")
    )

    # Join populations with city info (inner join to filter to canonical cities only)
    merged = populations.join(cities, on="city_id", how="inner")

    return merged


# =============================================================================
# Ranking Computation
# =============================================================================


def compute_rankings(df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute global, continental, and national rankings per epoch using DuckDB.

    Rankings are computed separately for each epoch using PARTITION BY epoch.

    Args:
        df: DataFrame with city_id, epoch, population, density_per_km2, country_code, continent

    Returns:
        DataFrame with all ranking columns added
    """
    conn = duckdb.connect()
    conn.register("city_data", df)

    query = """
    SELECT
        city_id,
        name,
        epoch,
        population,
        area_km2,
        density_per_km2,
        cell_count,
        country_code,
        continent,

        -- Global population rankings (per epoch)
        RANK() OVER (PARTITION BY epoch ORDER BY population DESC) as global_population_rank,
        PERCENT_RANK() OVER (PARTITION BY epoch ORDER BY population DESC) * 100 as global_population_percentile,

        -- Global density rankings (per epoch)
        RANK() OVER (PARTITION BY epoch ORDER BY density_per_km2 DESC) as global_density_rank,
        PERCENT_RANK() OVER (PARTITION BY epoch ORDER BY density_per_km2 DESC) * 100 as global_density_percentile,

        -- National rankings (per epoch, per country)
        RANK() OVER (PARTITION BY epoch, country_code ORDER BY population DESC) as national_population_rank,
        PERCENT_RANK() OVER (PARTITION BY epoch, country_code ORDER BY population DESC) * 100 as national_population_percentile,
        COUNT(*) OVER (PARTITION BY epoch, country_code) as country_city_count,

        -- Continental rankings (per epoch, per continent - NULL if no continent)
        CASE WHEN continent IS NOT NULL THEN
            RANK() OVER (PARTITION BY epoch, continent ORDER BY population DESC)
        END as continental_population_rank,
        CASE WHEN continent IS NOT NULL THEN
            PERCENT_RANK() OVER (PARTITION BY epoch, continent ORDER BY population DESC) * 100
        END as continental_population_percentile,
        COUNT(*) OVER (PARTITION BY epoch, continent) as continent_city_count

    FROM city_data
    ORDER BY epoch, global_population_rank
    """

    result = conn.execute(query).pl()
    conn.close()

    return result


def compute_per_epoch_growth(df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute 5-year CAGR growth rates between adjacent epochs.

    Adds:
      - growth_from_prev: CAGR from previous epoch (null for 1975)
      - growth_to_next: CAGR to next epoch (null for 2030)

    Args:
        df: DataFrame with rankings (must have city_id, epoch, population)

    Returns:
        DataFrame with growth columns added
    """
    conn = duckdb.connect()
    conn.register("ranked_data", df)

    query = """
    SELECT
        *,
        -- Get previous and next epoch populations using LAG/LEAD
        LAG(population) OVER (PARTITION BY city_id ORDER BY epoch) as prev_population,
        LEAD(population) OVER (PARTITION BY city_id ORDER BY epoch) as next_population,
        LAG(epoch) OVER (PARTITION BY city_id ORDER BY epoch) as prev_epoch,
        LEAD(epoch) OVER (PARTITION BY city_id ORDER BY epoch) as next_epoch
    FROM ranked_data
    """

    with_neighbors = conn.execute(query).pl()
    conn.close()

    # Calculate CAGRs using Polars
    # growth_from_prev: (population / prev_population)^(1/years) - 1
    # growth_to_next: (next_population / population)^(1/years) - 1

    with_growth = with_neighbors.with_columns([
        # Growth from previous epoch
        pl.when(pl.col("prev_population").is_not_null() & (pl.col("prev_population") > 0))
        .then(
            (pl.col("population") / pl.col("prev_population")).pow(
                1.0 / (pl.col("epoch") - pl.col("prev_epoch"))
            ) - 1
        )
        .otherwise(None)
        .alias("growth_from_prev"),

        # Growth to next epoch
        pl.when(pl.col("next_population").is_not_null() & (pl.col("population") > 0))
        .then(
            (pl.col("next_population") / pl.col("population")).pow(
                1.0 / (pl.col("next_epoch") - pl.col("epoch"))
            ) - 1
        )
        .otherwise(None)
        .alias("growth_to_next"),
    ])

    # Drop helper columns
    with_growth = with_growth.drop(["prev_population", "next_population", "prev_epoch", "next_epoch"])

    return with_growth


# =============================================================================
# Full-Period Growth Computation
# =============================================================================


def compute_full_period_growth(df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute full-period (1975-2030) growth metrics for each city.

    Output schema (city_growth.parquet):
      - city_id: String
      - cagr_1975_2030: Float64 - 55-year compound annual growth rate
      - growth_regime: String - explosive/growing/stable/shrinking
      - relative_acceleration: Float64 - vs world baseline (percentage points)
      - world_baseline_cagr: Float64 - World CAGR for reference

    Args:
        df: DataFrame with city_id, epoch, population

    Returns:
        DataFrame with one row per city containing growth metrics
    """
    # Filter to 1975 and 2030 only
    endpoints = df.filter(pl.col("epoch").is_in([1975, 2030])).select(
        ["city_id", "epoch", "population"]
    )

    # Pivot to get pop_1975 and pop_2030 columns
    pivoted = endpoints.pivot(
        on="epoch",
        index="city_id",
        values="population",
    ).rename({"1975": "pop_1975", "2030": "pop_2030"})

    # Calculate world baseline CAGR
    world_baseline = calculate_cagr(WORLD_POPULATION[1975], WORLD_POPULATION[2030], 55)

    # Calculate CAGR for each city
    growth = pivoted.with_columns([
        # 55-year CAGR
        pl.when((pl.col("pop_1975") > 0) & (pl.col("pop_2030") > 0))
        .then((pl.col("pop_2030") / pl.col("pop_1975")).pow(1.0 / 55) - 1)
        .otherwise(None)
        .alias("cagr_1975_2030"),

        # World baseline as constant
        pl.lit(world_baseline).alias("world_baseline_cagr"),
    ])

    # Add growth regime classification
    growth = growth.with_columns(
        pl.col("cagr_1975_2030")
        .map_elements(classify_growth_regime, return_dtype=pl.String)
        .alias("growth_regime")
    )

    # Calculate relative acceleration (percentage points vs world)
    growth = growth.with_columns(
        pl.when(pl.col("cagr_1975_2030").is_not_null())
        .then((pl.col("cagr_1975_2030") - pl.col("world_baseline_cagr")) * 100)
        .otherwise(None)
        .alias("relative_acceleration")
    )

    # Select final columns
    return growth.select([
        "city_id",
        "cagr_1975_2030",
        "growth_regime",
        "relative_acceleration",
        "world_baseline_cagr",
    ])


# =============================================================================
# Density Peers Computation
# =============================================================================


def compute_density_peers(df: pl.DataFrame, max_peers: int = 5, population_tolerance: float = 0.20) -> pl.DataFrame:
    """
    Find density peers for each city at 2030.

    For each city, finds other cities with similar population (+/-20%) but diverse densities,
    selecting from quintile positions (0%, 25%, 50%, 75%, 100%) of the density distribution.

    Output schema (city_density_peers.parquet):
      - city_id: String - Source city
      - peer_city_id: String - Peer city
      - peer_name: String - Peer city name
      - peer_population: Int64 - Peer population at 2030
      - peer_density: Float64 - Peer density per km²
      - density_ratio: Float64 - Peer density / source density

    Args:
        df: DataFrame with city data (must have epoch=2030 rows)
        max_peers: Maximum peers per city (default: 5)
        population_tolerance: Fraction tolerance for population similarity (default: 0.20)

    Returns:
        DataFrame with peer relationships
    """
    # Filter to 2030 data only
    data_2030 = df.filter(pl.col("epoch") == 2030).select([
        "city_id", "name", "population", "density_per_km2"
    ])

    # Convert to list for processing
    cities = data_2030.to_dicts()

    # Build index for efficient lookup
    city_lookup = {c["city_id"]: c for c in cities}

    peer_records = []

    for city in cities:
        target_id = city["city_id"]
        target_pop = city["population"]
        target_density = city["density_per_km2"]

        if target_pop <= 0 or target_density is None or target_density <= 0:
            continue

        min_pop = target_pop * (1 - population_tolerance)
        max_pop = target_pop * (1 + population_tolerance)

        # Filter candidates with similar population
        candidates = []
        for c in cities:
            if c["city_id"] == target_id:
                continue
            c_pop = c["population"]
            c_density = c["density_per_km2"]
            if min_pop <= c_pop <= max_pop and c_density is not None and c_density > 0:
                candidates.append(c)

        if not candidates:
            continue

        # Sort by density
        candidates.sort(key=lambda x: x["density_per_km2"])

        # Select from quintile positions
        n = len(candidates)
        if n <= max_peers:
            selected = candidates
        else:
            indices = [0, n // 4, n // 2, 3 * n // 4, n - 1]
            seen = set()
            unique_indices = []
            for i in indices:
                if i not in seen:
                    seen.add(i)
                    unique_indices.append(i)
            selected = [candidates[i] for i in unique_indices[:max_peers]]

        # Create peer records
        for peer in selected:
            peer_records.append({
                "city_id": target_id,
                "peer_city_id": peer["city_id"],
                "peer_name": peer["name"],
                "peer_population": int(peer["population"]),
                "peer_density": round(peer["density_per_km2"], 1),
                "density_ratio": round(peer["density_per_km2"] / target_density, 2),
            })

    return pl.DataFrame(peer_records)


# =============================================================================
# Main
# =============================================================================


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing outputs")
def main(force: bool = False):
    """Compute city rankings per epoch and growth metrics."""
    print("=" * 60)
    print("City Rankings Computation (Per-Epoch)")
    print("=" * 60)

    # Paths
    output_dir = get_processed_path("cities")
    rankings_path = output_dir / "city_rankings.parquet"
    growth_path = output_dir / "city_growth.parquet"
    peers_path = output_dir / "city_density_peers.parquet"

    # Check existing outputs
    if not force and rankings_path.exists():
        print(f"Output already exists: {rankings_path}")
        print("Use --force to overwrite")
        return

    # Load and prepare data
    print("\nLoading data...")
    df = load_data()
    n_cities = df["city_id"].n_unique()
    n_epochs = df["epoch"].n_unique()
    print(f"  Loaded {len(df):,} rows ({n_cities:,} cities × {n_epochs} epochs)")

    # Compute rankings per epoch
    print("\nComputing per-epoch rankings...")
    ranked = compute_rankings(df)
    print(f"  Computed rankings for {len(ranked):,} city-epoch combinations")

    # Compute per-epoch growth rates
    print("\nComputing per-epoch growth rates...")
    with_growth = compute_per_epoch_growth(ranked)

    # Save rankings
    print(f"\nSaving rankings to {rankings_path}...")
    with_growth.write_parquet(rankings_path)

    # Compute full-period growth
    print("\nComputing full-period growth metrics...")
    growth = compute_full_period_growth(df)
    print(f"  Computed growth for {len(growth):,} cities")

    # Save growth
    print(f"Saving growth to {growth_path}...")
    growth.write_parquet(growth_path)

    # Compute density peers
    print("\nComputing density peers (2030)...")
    peers = compute_density_peers(df)
    print(f"  Found {len(peers):,} peer relationships")

    # Save peers
    print(f"Saving peers to {peers_path}...")
    peers.write_parquet(peers_path)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    # Top 10 by population at 2030
    top_2030 = (
        with_growth.filter(pl.col("epoch") == 2030)
        .sort("global_population_rank")
        .head(10)
    )
    print("\nTop 10 cities by population (2030):")
    for row in top_2030.to_dicts():
        print(f"  {row['global_population_rank']:3d}. {row['name']} ({row['country_code']}): {row['population']:,.0f}")

    # Top 10 by density at 2030
    top_density = (
        with_growth.filter(pl.col("epoch") == 2030)
        .sort("global_density_rank")
        .head(10)
    )
    print("\nTop 10 cities by density (2030):")
    for row in top_density.to_dicts():
        print(f"  {row['global_density_rank']:3d}. {row['name']} ({row['country_code']}): {row['density_per_km2']:,.0f}/km²")

    # Growth regimes
    regime_counts = growth.group_by("growth_regime").len().sort("len", descending=True)
    print("\nGrowth regimes (1975-2030):")
    for row in regime_counts.to_dicts():
        regime = row["growth_regime"] or "unknown"
        print(f"  {regime}: {row['len']:,}")

    # Epoch coverage
    epochs = sorted(with_growth["epoch"].unique().to_list())
    print(f"\nEpochs covered: {epochs}")

    print(f"\nOutputs:")
    print(f"  Rankings: {rankings_path}")
    print(f"  Growth: {growth_path}")
    print(f"  Peers: {peers_path}")


if __name__ == "__main__":
    main()

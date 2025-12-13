"""
03b - Load 100m H3 population data into PostGIS (Greater Paris only).

Purpose: Load H3 resolution 9 population data from parquet into PostGIS,
         filtered to Greater Paris bounding box for efficient QGIS visualization.
Usage:
  uv run python src/s03b_load_h3_r9.py
  uv run python src/s03b_load_h3_r9.py --dry-run  # Show what would be done

Prerequisites:
  - PostGIS with H3 extension running (docker-compose up -d)
  - Database credentials in .env file:
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=urbanworld
    DB_USER=postgres
    DB_PASSWORD=postgres
  - Parquet file exists: data/processed/ghsl_pop_100m/h3_r9_pop_2025.parquet
    (run s03a_download_h3_r9.py first if needed)

Output: h3_pop_100m table in PostGIS database (Greater Paris only, ~500k-1M rows)
Date: 2024-12-13
"""

import os
import time
from pathlib import Path

import click
import duckdb
import psycopg2
from dotenv import load_dotenv

# Load environment variables from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Data paths
INPUT_FILE = Path("data/processed/ghsl_pop_100m/h3_r9_pop_2025.parquet")
TABLE_NAME = "h3_pop_100m"

# Greater Paris bounding box (Île-de-France + surroundings)
BBOX = {
    "min_lat": 48.1,
    "max_lat": 49.3,
    "min_lng": 1.4,
    "max_lng": 3.6,
}


def get_connection_string() -> str:
    """Build PostgreSQL connection string from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "urbanworld")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
def main(dry_run: bool = False):
    """Load 100m H3 population data into PostGIS (Greater Paris only)."""
    print("=" * 60)
    print("Load 100m H3 Population Data into PostGIS")
    print("Greater Paris Region Only")
    print("=" * 60)

    # Verify input file exists
    if not INPUT_FILE.exists():
        print(f"\nError: Input file not found: {INPUT_FILE}")
        print("Run s03a_download_h3_r9.py first to download the data.")
        return

    file_size_mb = INPUT_FILE.stat().st_size / 1e6
    print(f"\nInput file: {INPUT_FILE}")
    print(f"  Size: {file_size_mb:.1f} MB")

    # Connect to DuckDB and load h3 extension
    conn = duckdb.connect()
    conn.execute("INSTALL h3 FROM community")
    conn.execute("LOAD h3")

    # Get total row count
    total_count = conn.execute(
        f"SELECT COUNT(*) FROM read_parquet('{INPUT_FILE}')"
    ).fetchone()[0]
    print(f"  Total rows: {total_count:,}")

    # Filter by Greater Paris bounding box using DuckDB h3 extension
    print(f"\nFiltering to Greater Paris bbox:")
    print(f"  Lat: {BBOX['min_lat']} to {BBOX['max_lat']}")
    print(f"  Lng: {BBOX['min_lng']} to {BBOX['max_lng']}")

    filter_query = f"""
        SELECT h3_index, population
        FROM read_parquet('{INPUT_FILE}')
        WHERE h3_cell_to_lat(h3_index) BETWEEN {BBOX['min_lat']} AND {BBOX['max_lat']}
          AND h3_cell_to_lng(h3_index) BETWEEN {BBOX['min_lng']} AND {BBOX['max_lng']}
    """

    filtered_count = conn.execute(
        f"SELECT COUNT(*) FROM ({filter_query})"
    ).fetchone()[0]
    print(f"  Filtered rows: {filtered_count:,} ({filtered_count/total_count*100:.2f}%)")

    if dry_run:
        print("\n[DRY RUN] Would execute:")
        print(f"  1. DROP TABLE IF EXISTS {TABLE_NAME}")
        print(f"  2. CREATE TABLE {TABLE_NAME} (h3_index, population, geom)")
        print(f"  3. INSERT {filtered_count:,} rows from parquet (filtered)")
        print("  4. UPDATE geom column with h3_cell_to_boundary_geometry()")
        print("  5. CREATE SPATIAL INDEX on geom")
        return

    # Connect to PostgreSQL via DuckDB
    print("\nConnecting to PostgreSQL...")
    conn_string = get_connection_string()

    conn.execute("INSTALL postgres")
    conn.execute("LOAD postgres")
    conn.execute(f"ATTACH '{conn_string}' AS pg (TYPE postgres)")

    print("  Connected!")

    # Drop existing table
    print(f"\nDropping existing table {TABLE_NAME} if exists...")
    conn.execute(f"DROP TABLE IF EXISTS pg.{TABLE_NAME}")

    # Create table (without geometry - will add via PostgreSQL)
    print(f"Creating table {TABLE_NAME}...")
    conn.execute(f"""
        CREATE TABLE pg.{TABLE_NAME} (
            h3_index BIGINT PRIMARY KEY,
            population DOUBLE PRECISION NOT NULL
        )
    """)

    # Load filtered data
    print(f"\nLoading {filtered_count:,} rows from parquet (filtered)...")
    start_time = time.time()

    conn.execute(f"""
        INSERT INTO pg.{TABLE_NAME} (h3_index, population)
        {filter_query}
    """)

    load_time = time.time() - start_time
    rows_per_sec = filtered_count / load_time
    print(f"  Loaded in {load_time:.1f}s ({rows_per_sec:,.0f} rows/sec)")

    # Add geometry column and compute geometries in PostgreSQL
    # Use psycopg2 for PostgreSQL-specific operations (H3 extension functions)
    print("\nConnecting to PostgreSQL for geometry operations...")

    pg_conn = psycopg2.connect(conn_string)
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor()

    # Ensure H3 extensions are loaded
    print("Ensuring H3 extensions are loaded...")
    pg_cur.execute("CREATE EXTENSION IF NOT EXISTS h3 CASCADE")
    pg_cur.execute("CREATE EXTENSION IF NOT EXISTS h3_postgis CASCADE")

    print("Adding geometry column...")
    start_time = time.time()

    pg_cur.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN geom geometry(Polygon, 4326)")

    print("Computing H3 cell boundaries...")
    pg_cur.execute(f"""
        UPDATE {TABLE_NAME}
        SET geom = h3_cell_to_boundary_geometry(h3_index::h3index)
    """)
    print(f"  Geometry computed in {time.time() - start_time:.1f}s")

    # Create spatial index
    print("\nCreating spatial index...")
    start_time = time.time()
    pg_cur.execute(f"CREATE INDEX idx_{TABLE_NAME}_geom ON {TABLE_NAME} USING GIST(geom)")
    print(f"  Index created in {time.time() - start_time:.1f}s")

    pg_cur.close()
    pg_conn.close()

    # Verify
    print("\nVerifying load...")
    result = conn.execute(f"SELECT COUNT(*) FROM pg.{TABLE_NAME}").fetchone()
    loaded_count = result[0]

    if loaded_count == filtered_count:
        print(f"  SUCCESS: {loaded_count:,} rows loaded")
    else:
        print(f"  WARNING: Expected {filtered_count:,} rows, got {loaded_count:,}")

    # Sample query
    print("\nSample query (top 5 populated cells):")
    sample = conn.execute(f"""
        SELECT h3_index, population
        FROM pg.{TABLE_NAME}
        ORDER BY population DESC
        LIMIT 5
    """).fetchall()
    for row in sample:
        h3_idx, pop = row
        print(f"  h3={h3_idx}, pop={pop:.1f}")

    print("\n" + "=" * 60)
    print("Load complete!")
    print(f"Table '{TABLE_NAME}' ready for QGIS visualization")
    print("=" * 60)


if __name__ == "__main__":
    main()

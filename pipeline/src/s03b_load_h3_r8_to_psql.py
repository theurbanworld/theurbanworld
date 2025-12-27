"""
Load 1km H3 population time series data into PostGIS (Greater Paris only).

Purpose: Load H3 resolution 8 population time series from parquet into PostGIS,
         filtered to Greater Paris bounding box for efficient QGIS visualization.
Usage:
  uv run python -m src.s03b_load_h3_r8_to_psql
  uv run python -m src.s03b_load_h3_r8_to_psql --dry-run  # Show what would be done

Prerequisites:
  - PostGIS with H3 extension running (docker-compose up -d)
  - Database credentials in .env file:
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=urbanworld
    DB_USER=postgres
    DB_PASSWORD=postgres
  - Parquet files exist: data/processed/ghsl_pop_1km/h3_r8_pop_*.parquet
    (run s03a_download_h3_r8 first if needed)

Output: h3_pop_1km table in PostGIS database (Greater Paris only)
Date: 2025-12-13
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
INPUT_DIR = Path("data/processed/ghsl_pop_1km")
INPUT_FILE = INPUT_DIR / "h3_r8_pop_timeseries.parquet"
TABLE_NAME = "h3_pop_1km"

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
    """Load 1km H3 population time series into PostGIS (Greater Paris only)."""
    print("=" * 60)
    print("Load 1km H3 Population Time Series into PostGIS")
    print("Greater Paris Region Only")
    print("=" * 60)

    # Connect to DuckDB and load h3 extension
    conn = duckdb.connect()
    conn.execute("INSTALL h3 FROM community")
    conn.execute("LOAD h3")

    # Build bbox filter clause
    bbox_filter = f"""
        h3_cell_to_lat(h3_index) BETWEEN {BBOX['min_lat']} AND {BBOX['max_lat']}
        AND h3_cell_to_lng(h3_index) BETWEEN {BBOX['min_lng']} AND {BBOX['max_lng']}
    """

    if INPUT_FILE.exists():
        print(f"\nUsing timeseries file: {INPUT_FILE}")
        file_size_mb = INPUT_FILE.stat().st_size / 1e6
        print(f"  Size: {file_size_mb:.1f} MB")

        # Get schema to determine available epochs
        schema = conn.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{INPUT_FILE}')"
        ).fetchall()
        columns = [row[0] for row in schema]
        available_epochs = [
            int(c.replace("pop_", "")) for c in columns if c.startswith("pop_")
        ]
        print(f"  Epochs: {available_epochs}")

        total_count = conn.execute(
            f"SELECT COUNT(*) FROM read_parquet('{INPUT_FILE}')"
        ).fetchone()[0]
        print(f"  Total rows: {total_count:,}")

        epoch_columns = [f"pop_{e}" for e in available_epochs]
        select_cols = ["h3_index"] + epoch_columns

        source_query = f"""
            SELECT {', '.join(select_cols)}
            FROM read_parquet('{INPUT_FILE}')
            WHERE {bbox_filter}
        """
    else:
        # Build from individual epoch files
        print("\nNo timeseries file found, checking for individual epoch files...")
        epoch_files = sorted(INPUT_DIR.glob("h3_r8_pop_[0-9][0-9][0-9][0-9].parquet"))

        if not epoch_files:
            print(f"Error: No parquet files found in {INPUT_DIR}")
            print("Run s04a_download_h3_r8.py first to download the data.")
            return

        available_epochs = [int(f.stem.split("_")[-1]) for f in epoch_files]
        print(f"  Found epochs: {available_epochs}")

        # Build pivot query using DuckDB with bbox filter
        union_parts = []
        for epoch in available_epochs:
            epoch_file = INPUT_DIR / f"h3_r8_pop_{epoch}.parquet"
            union_parts.append(
                f"SELECT h3_index, population, {epoch} as year "
                f"FROM read_parquet('{epoch_file}') "
                f"WHERE {bbox_filter}"
            )

        union_query = " UNION ALL ".join(union_parts)
        pivot_cols = ", ".join(
            [
                f"SUM(CASE WHEN year = {e} THEN population ELSE 0 END) as pop_{e}"
                for e in available_epochs
            ]
        )

        source_query = f"""
            SELECT h3_index, {pivot_cols}
            FROM ({union_query})
            GROUP BY h3_index
        """
        epoch_columns = [f"pop_{e}" for e in available_epochs]

        total_count = conn.execute(
            f"SELECT COUNT(DISTINCT h3_index) FROM ({' UNION ALL '.join([f'SELECT h3_index FROM read_parquet({repr(str(f))})' for f in epoch_files])})"
        ).fetchone()[0]
        print(f"  Total unique H3 cells: {total_count:,}")

    # Get filtered count
    print(f"\nFiltering to Greater Paris bbox:")
    print(f"  Lat: {BBOX['min_lat']} to {BBOX['max_lat']}")
    print(f"  Lng: {BBOX['min_lng']} to {BBOX['max_lng']}")

    filtered_count = conn.execute(
        f"SELECT COUNT(*) FROM ({source_query})"
    ).fetchone()[0]
    print(f"  Filtered rows: {filtered_count:,}")

    if dry_run:
        print("\n[DRY RUN] Would execute:")
        print(f"  1. DROP TABLE IF EXISTS {TABLE_NAME}")
        print(
            f"  2. CREATE TABLE {TABLE_NAME} with columns: h3_index, "
            f"{', '.join(epoch_columns)}, geom"
        )
        print(f"  3. INSERT {filtered_count:,} rows (filtered)")
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

    # Create table with all epoch columns (without geometry - will add via PostgreSQL)
    col_defs = ["h3_index BIGINT PRIMARY KEY"]
    col_defs.extend([f"pop_{e} DOUBLE PRECISION" for e in available_epochs])
    create_sql = f"CREATE TABLE pg.{TABLE_NAME} ({', '.join(col_defs)})"

    print(f"Creating table {TABLE_NAME}...")
    conn.execute(create_sql)

    # Load filtered data
    print(f"\nLoading {filtered_count:,} rows (filtered)...")
    start_time = time.time()

    insert_cols = ["h3_index"] + epoch_columns
    conn.execute(f"""
        INSERT INTO pg.{TABLE_NAME} ({', '.join(insert_cols)})
        {source_query}
    """)

    load_time = time.time() - start_time
    rows_per_sec = filtered_count / load_time if load_time > 0 else 0
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
    print("\nSample query (top 3 cells by 2025 population with time series):")
    first_epoch = available_epochs[0] if available_epochs else 1975
    mid_epoch = available_epochs[len(available_epochs) // 2] if available_epochs else 2000
    last_epoch = available_epochs[-1] if available_epochs else 2025

    sample = conn.execute(f"""
        SELECT
            h3_index,
            pop_{first_epoch} as first_pop,
            pop_{mid_epoch} as mid_pop,
            pop_{last_epoch} as last_pop,
            (pop_{last_epoch} - pop_{first_epoch}) as growth
        FROM pg.{TABLE_NAME}
        ORDER BY pop_{last_epoch} DESC
        LIMIT 3
    """).fetchall()
    for row in sample:
        h3_idx, first_pop, mid_pop, last_pop, growth = row
        print(
            f"  h3={h3_idx}: {first_epoch}={first_pop:.0f}, "
            f"{mid_epoch}={mid_pop:.0f}, {last_epoch}={last_pop:.0f}, "
            f"growth={growth:+.0f}"
        )

    print("\n" + "=" * 60)
    print("Load complete!")
    print(f"Table '{TABLE_NAME}' ready for QGIS visualization")
    print("=" * 60)


if __name__ == "__main__":
    main()

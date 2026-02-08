"""
Merge H3 population data into timeseries format.

Purpose: Combine all yearly H3 population files into a single wide-format
         parquet file for efficient frontend loading with time scrubbing.

Usage:
  uv run python -m src.s08_merge_h3_timeseries           # Generate and upload
  uv run python -m src.s08_merge_h3_timeseries --local   # Generate only (no upload)

Date: 2025-12-28
"""

import os
from pathlib import Path

import boto3
import polars as pl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
H3_POP_DIR = Path("data/processed/ghsl_pop_1km")
OUTPUT_PARQUET = Path("data/processed/tiles/h3_r8_pop_timeseries.parquet")
R2_KEY = "data/h3_r8_pop_timeseries.parquet"
EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]


def load_and_merge_epochs() -> pl.DataFrame:
    """Load all yearly H3 files and merge into wide format."""
    print(f"Loading H3 population files from {H3_POP_DIR}...")

    # Collect all data in long format first
    all_data = []
    for epoch in EPOCHS:
        file_path = H3_POP_DIR / f"h3_r8_pop_{epoch}.parquet"
        if not file_path.exists():
            print(f"  Warning: {file_path} not found, skipping")
            continue

        df = pl.read_parquet(file_path)
        df = df.with_columns(pl.lit(epoch).alias("epoch"))
        all_data.append(df)
        print(f"  Loaded {epoch}: {len(df):,} cells")

    if not all_data:
        raise FileNotFoundError("No H3 population files found")

    # Concatenate all epochs
    combined = pl.concat(all_data)
    print(f"\nCombined: {len(combined):,} total rows")

    # Get unique h3_index -> city_id mapping (use most recent city_id for each cell)
    cell_cities = (
        combined
        .sort("epoch", descending=True)
        .group_by("h3_index")
        .first()
        .select(["h3_index", "city_id"])
    )

    # Pivot to wide format
    print("Pivoting to wide format...")
    pivoted = (
        combined
        .pivot(
            on="epoch",
            index="h3_index",
            values="population",
        )
    )

    # Rename columns from epoch numbers to pop_YYYY
    rename_map = {str(e): f"pop_{e}" for e in EPOCHS}
    pivoted = pivoted.rename(rename_map)

    # Join city_id back
    result = pivoted.join(cell_cities, on="h3_index", how="left")

    # Fill nulls with 0 (cells that didn't exist in some years)
    pop_cols = [f"pop_{e}" for e in EPOCHS if f"pop_{e}" in result.columns]
    result = result.with_columns([
        pl.col(col).fill_null(0.0) for col in pop_cols
    ])

    # Convert h3_index from int64 to hex string for browser compatibility
    # (JavaScript can't handle int64 values > Number.MAX_SAFE_INTEGER)
    result = result.with_columns(
        pl.col("h3_index").map_elements(
            lambda x: format(x, 'x'),
            return_dtype=pl.Utf8
        ).alias("h3_index")
    )

    # Ensure consistent column order
    ordered_cols = ["h3_index", "city_id"] + pop_cols
    result = result.select([c for c in ordered_cols if c in result.columns])

    print(f"\nMerged timeseries: {len(result):,} unique H3 cells")
    print(f"Columns: {result.columns}")

    return result


def save_parquet(df: pl.DataFrame, output_path: Path) -> None:
    """Save DataFrame to parquet with snappy compression (browser-compatible)."""
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Use snappy compression for browser compatibility
    # (zstd default causes issues with @loaders.gl/parquet in browsers)
    df.write_parquet(output_path, compression="snappy")
    file_size = output_path.stat().st_size / 1e6
    print(f"  Saved {output_path} ({file_size:.1f} MB)")


def upload_to_r2(local_path: Path, r2_key: str) -> str:
    """Upload parquet to R2."""
    print(f"\nUploading to R2...")

    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["R2_BUCKET_NAME"]

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    file_size = local_path.stat().st_size / 1e6
    print(f"  Uploading {local_path.name} ({file_size:.1f} MB) -> {r2_key}")

    s3.upload_file(
        str(local_path),
        bucket_name,
        r2_key,
        ExtraArgs={"ContentType": "application/vnd.apache.parquet"},
    )

    print(f"  Uploaded to s3://{bucket_name}/{r2_key}")
    return f"s3://{bucket_name}/{r2_key}"


def main(local_only: bool = False) -> None:
    """Merge H3 population files and upload to R2."""
    print("=" * 60)
    print("H3 Population Timeseries Generator")
    print("=" * 60)

    # Load and merge
    df = load_and_merge_epochs()

    # Save locally
    save_parquet(df, OUTPUT_PARQUET)

    # Upload to R2
    if not local_only:
        upload_to_r2(OUTPUT_PARQUET, R2_KEY)
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_PARQUET}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge H3 population timeseries")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

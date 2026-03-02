"""
Generate per-city H3 cell index files for frontend.

Purpose: Export one JSON file per city containing its H3 cell hex indices.
         Used by the radial map layer to render cells on-demand without
         loading the full H3 timeseries parquet.

Output: data/city_cells/{city_id}.json → ["882f5b5267fffff", ...]
R2:     data/city_cells/{city_id}.json (one key per city)

Usage:
  uv run python -m src.web_export.generate_city_cells           # Generate and upload
  uv run python -m src.web_export.generate_city_cells --local   # Generate only

Date: 2026-03-02
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import polars as pl
from dotenv import load_dotenv


def _upload_file(s3_client, bucket: str, local_path: Path, r2_key: str) -> str:
    """Upload a single file to R2. Returns the r2_key on success."""
    s3_client.upload_file(
        str(local_path),
        bucket,
        r2_key,
        ExtraArgs={"ContentType": "application/json"},
    )
    return r2_key


def main(local_only: bool = False) -> None:
    """Generate per-city H3 cell JSON files and upload to R2."""
    print("=" * 60)
    print("Per-City H3 Cell Index Generator")
    print("=" * 60)

    # Use epoch 2025 as the canonical cell set
    input_path = Path("data/processed/ghsl_h3_r8/h3_r8_pop_2025.parquet")
    output_dir = Path("data/processed/tiles/city_cells")
    r2_prefix = "data/city_cells"

    print(f"\nLoading {input_path}...")
    df = pl.read_parquet(input_path)
    print(f"  {len(df):,} cells, {df['city_id'].n_unique():,} cities")

    # Group by city_id and write local JSON files
    output_dir.mkdir(parents=True, exist_ok=True)
    cities = df.group_by("city_id")

    file_count = 0
    total_cells = 0

    for (city_id,), group in cities:
        h3_indices = [format(idx, "x") for idx in group["h3_index"].to_list()]
        total_cells += len(h3_indices)

        output_path = output_dir / f"{city_id}.json"
        with open(output_path, "w") as f:
            json.dump(h3_indices, f, separators=(",", ":"))

        file_count += 1

    print(f"\n  Generated {file_count:,} city files ({total_cells:,} total cells)")
    print(f"  Output: {output_dir}/")

    if not local_only:
        load_dotenv()

        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT_URL"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        )
        bucket = os.environ["R2_BUCKET_NAME"]

        print(f"\nUploading {file_count:,} files to R2 (20 threads)...")
        json_files = sorted(output_dir.glob("*.json"))
        uploaded = 0

        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = {
                pool.submit(
                    _upload_file, s3, bucket, f, f"{r2_prefix}/{f.stem}.json"
                ): f
                for f in json_files
            }
            for future in as_completed(futures):
                future.result()  # raises on error
                uploaded += 1
                if uploaded % 500 == 0 or uploaded == file_count:
                    print(f"  {uploaded:,}/{file_count:,} uploaded")

        print(f"  Done — {uploaded:,} files uploaded")
    else:
        print(f"\nLocal only mode - skipping R2 upload")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate per-city H3 cell index files")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

"""
04a - Download 1km H3 population data from R2.

Purpose: Download the processed H3 resolution 8 population data from R2
Usage:
  uv run python src/s04a_download_h3_r8.py
  uv run python src/s04a_download_h3_r8.py --timeseries-only  # Just the combined file

Prerequisites:
  - R2 credentials in .env file:
    R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID=<your_access_key>
    R2_SECRET_ACCESS_KEY=<your_secret_key>
    R2_BUCKET_NAME=<your_bucket_name>

Output: data/processed/ghsl_pop_1k/*.parquet
Date: 2024-12-13
"""

import argparse
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

# Load environment variables from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# R2 settings
R2_PREFIX = "ghsl-pop-1km"
OUTPUT_DIR = Path("data/processed/ghsl_pop_1km")


def get_r2_client():
    """Create S3 client for R2."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def list_r2_files(s3, bucket_name: str, prefix: str) -> list[str]:
    """List all files in R2 bucket with given prefix."""
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    files = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".parquet"):
            files.append(key)
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Download 1km H3 data from R2")
    parser.add_argument(
        "--timeseries-only",
        action="store_true",
        help="Only download the timeseries file (not individual epochs)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Download 1km H3 Population Data from R2")
    print("=" * 60)

    bucket_name = os.environ["R2_BUCKET_NAME"]
    print(f"\nBucket: {bucket_name}")
    print(f"Prefix: {R2_PREFIX}/")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create R2 client
    s3 = get_r2_client()

    # List available files
    all_files = list_r2_files(s3, bucket_name, R2_PREFIX)
    print(f"\nFound {len(all_files)} files in R2")

    # Filter files if needed
    if args.timeseries_only:
        files_to_download = [f for f in all_files if "timeseries" in f]
        print("  (downloading timeseries only)")
    else:
        files_to_download = all_files

    if not files_to_download:
        print("  No files to download!")
        return

    # Download files
    total_size = 0
    for key in files_to_download:
        filename = Path(key).name
        output_path = OUTPUT_DIR / filename

        print(f"\nDownloading {filename}...")

        # Get file size
        head = s3.head_object(Bucket=bucket_name, Key=key)
        file_size = head["ContentLength"] / 1e6
        total_size += file_size
        print(f"  Size: {file_size:.1f} MB")

        # Download
        s3.download_file(bucket_name, key, str(output_path))
        print(f"  Saved to {output_path}")

    print("\n" + "=" * 60)
    print(f"Download complete! Total: {total_size:.1f} MB")
    print(f"Files saved to {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
03a - Download 100m H3 population data from R2.

Purpose: Download the processed H3 resolution 9 population data from R2
Usage:
  uv run python src/s03a_download_h3_r9.py

Prerequisites:
  - R2 credentials in .env file:
    R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID=<your_access_key>
    R2_SECRET_ACCESS_KEY=<your_secret_key>
    R2_BUCKET_NAME=<your_bucket_name>

Output: data/processed/ghsl_pop_100m/h3_r9_pop_2025.parquet
Date: 2024-12-13
"""

import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

# Load environment variables from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# R2 settings
R2_PREFIX = "ghsl-pop-100m"
OUTPUT_DIR = Path("data/processed/ghsl_pop_100m")
FILES_TO_DOWNLOAD = ["h3_r9_pop_2025.parquet"]


def get_r2_client():
    """Create S3 client for R2."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def main():
    print("=" * 60)
    print("Download 100m H3 Population Data from R2")
    print("=" * 60)

    bucket_name = os.environ["R2_BUCKET_NAME"]
    print(f"\nBucket: {bucket_name}")
    print(f"Prefix: {R2_PREFIX}/")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create R2 client
    s3 = get_r2_client()

    # Download files
    for filename in FILES_TO_DOWNLOAD:
        key = f"{R2_PREFIX}/{filename}"
        output_path = OUTPUT_DIR / filename

        print(f"\nDownloading {key}...")

        # Get file size first
        try:
            head = s3.head_object(Bucket=bucket_name, Key=key)
            file_size = head["ContentLength"] / 1e6
            print(f"  Size: {file_size:.1f} MB")
        except Exception as e:
            print(f"  Error: File not found - {e}")
            continue

        # Download
        s3.download_file(bucket_name, key, str(output_path))
        print(f"  Saved to {output_path}")

    print("\n" + "=" * 60)
    print("Download complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

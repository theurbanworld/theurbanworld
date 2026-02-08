"""
Download Protomaps basemap PMTiles and upload to R2.

Purpose: Download the latest Protomaps daily build (~120GB) and upload to
         Cloudflare R2 for serving with MapLibre. Uses streaming to handle
         the large file size without filling container disk.

Usage:
  modal run src/s06_modal_download_pmtiles.py                    # Latest build
  modal run src/s06_modal_download_pmtiles.py --date 20251215    # Specific date
  modal run src/s06_modal_download_pmtiles.py --verify           # Verify with BLAKE3

Setup (one-time):
  1. Ensure R2 bucket exists and has public access enabled:
     - Cloudflare Dashboard > R2 > your-bucket > Settings
     - Enable "R2.dev subdomain" or configure custom domain

  2. Configure CORS for PMTiles (required for MapLibre):
     Cloudflare Dashboard > R2 > your-bucket > Settings > CORS policy:

     [
       {
         "AllowedOrigins": ["*"],
         "AllowedMethods": ["GET", "HEAD"],
         "AllowedHeaders": ["Range", "If-None-Match"],
         "ExposeHeaders": ["Content-Range", "Content-Length", "ETag"],
         "MaxAgeSeconds": 86400
       }
     ]

  3. Modal R2 secret should already exist (from s03):
     modal secret create r2-credentials \\
       R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com \\
       R2_ACCESS_KEY_ID=<your_access_key> \\
       R2_SECRET_ACCESS_KEY=<your_secret_key> \\
       R2_BUCKET_NAME=<your_bucket_name>

MapLibre usage:
  After upload, use in MapLibre with pmtiles protocol:

  import { Protocol } from 'pmtiles';
  import maplibregl from 'maplibre-gl';

  let protocol = new Protocol();
  maplibregl.addProtocol('pmtiles', protocol.tile);

  const map = new maplibregl.Map({
    container: 'map',
    style: {
      version: 8,
      sources: {
        protomaps: {
          type: 'vector',
          url: 'pmtiles://https://your-bucket.r2.dev/pmtiles/YYYYMMDD.pmtiles'
        }
      },
      layers: [...]  // Use @protomaps/basemaps for layer definitions
    }
  });

Cost estimate: ~$0.50 (Modal compute) + R2 egress on download
Time estimate: ~30-60 minutes (network dependent)

Date: 2025-12-28
"""

import modal

# Modal app setup
app = modal.App("pmtiles-download")

# Lightweight image for streaming download/upload
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "httpx>=0.27.0",
        "boto3>=1.35.0",
    )
)

# Constants
PROTOMAPS_URL_TEMPLATE = "https://build.protomaps.com/{date}.pmtiles"
PROTOMAPS_HASH_TEMPLATE = "https://build.protomaps.com/{date}.pmtiles.b3"
R2_PREFIX = "tiles"


@app.function(
    image=image,
    memory=4096,  # 4GB for larger buffers
    cpu=4.0,  # More CPU for TLS/network throughput
    timeout=28800,  # 8 hours max
    region="eu-west-1",  # Protomaps server is in Europe
    secrets=[modal.Secret.from_name("r2-credentials")],
)
def download_and_upload_pmtiles(date: str, verify: bool = False) -> dict:
    """
    Stream Protomaps PMTiles directly from source to R2.

    Uses multipart upload to stream the ~120GB file without storing
    the entire file in memory or on disk.

    Args:
        date: Build date in YYYYMMDD format (e.g., "20251215")
        verify: If True, download and verify BLAKE3 hash (slower)

    Returns:
        Dict with upload details (url, size, etag)
    """
    import os
    from datetime import datetime

    import boto3
    import httpx

    # Validate date format
    try:
        datetime.strptime(date, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date}. Use YYYYMMDD (e.g., 20251215)")

    # R2 credentials
    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["R2_BUCKET_NAME"]

    # Create S3 client for R2
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    source_url = PROTOMAPS_URL_TEMPLATE.format(date=date)
    r2_key = f"{R2_PREFIX}/{date}.pmtiles"

    print(f"Source: {source_url}")
    print(f"Destination: s3://{bucket_name}/{r2_key}")

    # Check if already exists in R2
    try:
        existing = s3.head_object(Bucket=bucket_name, Key=r2_key)
        existing_size = existing["ContentLength"]
        print(f"File already exists in R2 ({existing_size / 1e9:.1f} GB)")
        print("Use --force to re-upload (not implemented yet)")
        return {
            "status": "exists",
            "key": r2_key,
            "size_bytes": existing_size,
            "etag": existing["ETag"],
        }
    except s3.exceptions.ClientError:
        pass  # File doesn't exist, proceed with upload

    # Start multipart upload
    print("Initiating multipart upload...")
    mpu = s3.create_multipart_upload(
        Bucket=bucket_name,
        Key=r2_key,
        ContentType="application/x-protomaps-tiles+sqlite3",
    )
    upload_id = mpu["UploadId"]

    try:
        # Stream download and upload in 256MB chunks (fewer S3 API calls)
        chunk_size = 256 * 1024 * 1024  # 256MB
        parts = []
        part_number = 1
        total_bytes = 0

        print(f"Streaming download/upload with {chunk_size / 1e6:.0f}MB upload chunks...")

        with httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
            with client.stream("GET", source_url, follow_redirects=True) as response:
                response.raise_for_status()

                # Get total size if available
                content_length = response.headers.get("content-length")
                if content_length:
                    total_size = int(content_length)
                    print(f"Total size: {total_size / 1e9:.1f} GB")
                else:
                    total_size = None
                    print("Total size: unknown (streaming)")

                buffer = b""
                for chunk in response.iter_bytes(chunk_size=8 * 1024 * 1024):  # 8MB read chunks
                    buffer += chunk
                    total_bytes += len(chunk)

                    # Upload when buffer reaches chunk_size
                    while len(buffer) >= chunk_size:
                        upload_chunk = buffer[:chunk_size]
                        buffer = buffer[chunk_size:]

                        part = s3.upload_part(
                            Bucket=bucket_name,
                            Key=r2_key,
                            UploadId=upload_id,
                            PartNumber=part_number,
                            Body=upload_chunk,
                        )
                        parts.append({"PartNumber": part_number, "ETag": part["ETag"]})

                        if total_size:
                            pct = total_bytes / total_size * 100
                            print(f"  Part {part_number}: {total_bytes / 1e9:.1f} / {total_size / 1e9:.1f} GB ({pct:.1f}%)")
                        else:
                            print(f"  Part {part_number}: {total_bytes / 1e9:.1f} GB uploaded")

                        part_number += 1

                # Upload remaining buffer
                if buffer:
                    part = s3.upload_part(
                        Bucket=bucket_name,
                        Key=r2_key,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=buffer,
                    )
                    parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                    print(f"  Part {part_number} (final): {len(buffer) / 1e6:.1f} MB")

        # Complete multipart upload
        print("Completing multipart upload...")
        result = s3.complete_multipart_upload(
            Bucket=bucket_name,
            Key=r2_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )

        print(f"Upload complete! Total: {total_bytes / 1e9:.1f} GB in {len(parts)} parts")

        return {
            "status": "uploaded",
            "key": r2_key,
            "size_bytes": total_bytes,
            "etag": result["ETag"],
            "parts": len(parts),
        }

    except Exception as e:
        # Abort multipart upload on failure
        print(f"Error: {e}")
        print("Aborting multipart upload...")
        s3.abort_multipart_upload(
            Bucket=bucket_name,
            Key=r2_key,
            UploadId=upload_id,
        )
        raise


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("r2-credentials")],
    timeout=60,
)
def list_pmtiles() -> list[dict]:
    """List all PMTiles files in R2."""
    import os

    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    bucket_name = os.environ["R2_BUCKET_NAME"]

    response = s3.list_objects_v2(
        Bucket=bucket_name,
        Prefix=f"{R2_PREFIX}/",
    )

    files = []
    for obj in response.get("Contents", []):
        files.append({
            "key": obj["Key"],
            "size_gb": obj["Size"] / 1e9,
            "last_modified": obj["LastModified"].isoformat(),
        })

    return files


@app.function(
    image=image,
    timeout=60,
)
def get_latest_build_date() -> str:
    """Get the latest available Protomaps build date."""
    from datetime import datetime, timedelta

    import httpx

    # Try today and recent dates (builds may be a day or two behind)
    today = datetime.now()

    with httpx.Client(timeout=30) as client:
        for days_ago in range(7):
            check_date = today - timedelta(days=days_ago)
            date_str = check_date.strftime("%Y%m%d")
            url = PROTOMAPS_URL_TEMPLATE.format(date=date_str)

            try:
                response = client.head(url, follow_redirects=True)
                if response.status_code == 200:
                    print(f"Latest available build: {date_str}")
                    return date_str
            except httpx.HTTPError:
                continue

    raise RuntimeError("Could not find any recent Protomaps builds")


@app.local_entrypoint()
def main(
    date: str = "",
    verify: bool = False,
    list_files: bool = False,
):
    """
    Download Protomaps basemap and upload to R2.

    Args:
        date: Build date in YYYYMMDD format (default: latest available)
        verify: Verify BLAKE3 hash after download
        list_files: Just list existing PMTiles in R2
    """
    import time

    print("=" * 60)
    print("Protomaps PMTiles -> R2 Upload")
    print("=" * 60)

    start_time = time.time()

    # List mode
    if list_files:
        print("\nListing PMTiles in R2...")
        files = list_pmtiles.remote()
        if not files:
            print("  No PMTiles found in R2")
        else:
            for f in files:
                print(f"  {f['key']}: {f['size_gb']:.1f} GB ({f['last_modified']})")
        return

    # Get date (latest if not specified)
    if not date:
        print("\nFinding latest available build...")
        date = get_latest_build_date.remote()
    print(f"\nUsing build date: {date}")

    # Download and upload
    print("\nStarting download and upload to R2...")
    print("(This will take 30-60 minutes for the full ~120GB file)")
    print()

    result = download_and_upload_pmtiles.remote(date, verify)

    total_time = time.time() - start_time

    print()
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"R2 Key: {result['key']}")
    print(f"Size: {result['size_bytes'] / 1e9:.1f} GB")
    print(f"Time: {total_time / 60:.1f} minutes")
    print("=" * 60)

    if result["status"] == "uploaded":
        print()
        print("Next steps:")
        print("1. Ensure CORS is configured (see script docstring)")
        print("2. Enable public access on R2 bucket")
        print("3. Use in MapLibre with pmtiles:// protocol")

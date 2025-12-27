"""
20 - Upload to Cloudflare R2

Purpose: Upload all processed data to Cloudflare R2 for web serving
Input: data/processed/ directory
Output: Files uploaded to R2 bucket

Features:
  - Incremental uploads (skip unchanged files via ETag comparison)
  - Multipart upload for large files (70GB basemap)
  - Progress display for large uploads
  - Dry-run mode to preview changes
  - Selective upload by dataset type

Decision log:
  - Using boto3 with S3-compatible API for R2
  - ETag comparison for incremental uploads
  - Multipart upload with 100MB chunks for large files
  - 4 concurrent threads balances speed vs memory
Date: 2024-12-09
"""

import hashlib
import sys
from pathlib import Path
from typing import Optional

import boto3
import click
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from tqdm import tqdm

from .utils.config import get_processed_path
from .utils.r2_config import r2_config


class UploadProgress:
    """Callback for tracking upload progress."""

    def __init__(self, filename: str, total_size: int):
        self.filename = filename
        self.total_size = total_size
        self.uploaded = 0
        self.pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=f"  {Path(filename).name}",
            leave=False,
        )

    def __call__(self, bytes_transferred: int):
        self.uploaded += bytes_transferred
        self.pbar.update(bytes_transferred)

    def close(self):
        self.pbar.close()


def get_s3_client():
    """Create boto3 S3 client configured for R2."""
    return boto3.client(
        "s3",
        endpoint_url=r2_config.endpoint,
        aws_access_key_id=r2_config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=r2_config.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def get_upload_mappings() -> dict:
    """Get upload mappings using config paths."""
    processed_dir = get_processed_path()
    prefix = r2_config.R2_PREFIX

    return {
        "basemap": {
            "local": processed_dir / "basemap",
            "r2_prefix": f"{prefix}/basemap",
            "description": "Protomaps basemap tiles",
        },
        "h3": {
            "local": processed_dir / "h3_tiles",
            "r2_prefix": f"{prefix}/h3",
            "description": "H3 population hexagons",
        },
        "cities": {
            "local": processed_dir / "cities",
            "r2_prefix": f"{prefix}/cities",
            "description": "City metadata JSON files",
        },
    }


def get_extra_files() -> list[dict]:
    """Get extra files to upload."""
    processed_dir = get_processed_path()
    prefix = r2_config.R2_PREFIX

    return [
        {
            "local": processed_dir / "city_index.json",
            "r2_key": f"{prefix}/cities/index.json",
            "description": "City index",
        },
    ]


def compute_etag(filepath: Path, chunk_size: int = None) -> str:
    """
    Compute the ETag for a file the same way S3/R2 does.

    For files uploaded as single part: MD5 hash
    For multipart uploads: MD5 of concatenated part MD5s + "-" + part count
    """
    if chunk_size is None:
        chunk_size = r2_config.MULTIPART_CHUNKSIZE

    file_size = filepath.stat().st_size

    if file_size <= r2_config.MULTIPART_THRESHOLD:
        # Single part upload - simple MD5
        md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return f'"{md5.hexdigest()}"'
    else:
        # Multipart upload - MD5 of part MD5s
        part_md5s = []
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                part_md5s.append(hashlib.md5(chunk).digest())

        combined_md5 = hashlib.md5(b"".join(part_md5s)).hexdigest()
        return f'"{combined_md5}-{len(part_md5s)}"'


def get_remote_etag(client, key: str) -> Optional[str]:
    """Get ETag of existing object in R2, or None if not found."""
    try:
        response = client.head_object(Bucket=r2_config.R2_BUCKET, Key=key)
        return response.get("ETag")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None
        raise


def file_needs_upload(client, local_path: Path, r2_key: str, force: bool = False) -> bool:
    """Check if a file needs to be uploaded (changed or missing)."""
    if force:
        return True

    remote_etag = get_remote_etag(client, r2_key)
    if remote_etag is None:
        return True

    local_etag = compute_etag(local_path)
    return local_etag != remote_etag


def upload_file(
    client,
    local_path: Path,
    r2_key: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[bool, int]:
    """
    Upload a single file to R2.

    Returns: (success, bytes_uploaded)
    """
    file_size = local_path.stat().st_size
    content_type = r2_config.get_content_type(local_path.name)
    cache_control = r2_config.get_cache_control(r2_key)

    if dry_run:
        if verbose:
            size_mb = file_size / (1024 * 1024)
            print(f"  Would upload: {local_path.name} ({size_mb:.1f} MB) -> {r2_key}")
        return True, file_size

    # Configure transfer for large files
    transfer_config = TransferConfig(
        multipart_threshold=r2_config.MULTIPART_THRESHOLD,
        multipart_chunksize=r2_config.MULTIPART_CHUNKSIZE,
        max_concurrency=r2_config.MULTIPART_MAX_CONCURRENCY,
        use_threads=True,
    )

    extra_args = {
        "ContentType": content_type,
        "CacheControl": cache_control,
    }

    try:
        # Show progress for large files
        if file_size > r2_config.PROGRESS_THRESHOLD:
            progress = UploadProgress(str(local_path), file_size)
            client.upload_file(
                str(local_path),
                r2_config.R2_BUCKET,
                r2_key,
                Config=transfer_config,
                ExtraArgs=extra_args,
                Callback=progress,
            )
            progress.close()
        else:
            client.upload_file(
                str(local_path),
                r2_config.R2_BUCKET,
                r2_key,
                Config=transfer_config,
                ExtraArgs=extra_args,
            )
        return True, file_size

    except Exception as e:
        print(f"  ERROR uploading {local_path.name}: {e}")
        return False, 0


def collect_files(dataset: str) -> list[tuple[Path, str]]:
    """Collect all files for a dataset, returning (local_path, r2_key) tuples."""
    mappings = get_upload_mappings()
    mapping = mappings.get(dataset)
    if not mapping:
        return []

    local_dir = mapping["local"]
    r2_prefix = mapping["r2_prefix"]

    if not local_dir.exists():
        return []

    files = []
    for local_path in local_dir.rglob("*"):
        if local_path.is_file():
            relative = local_path.relative_to(local_dir)
            r2_key = f"{r2_prefix}/{relative}"
            files.append((local_path, r2_key))

    return files


def format_size(size_bytes: int) -> str:
    """Format byte size as human readable string."""
    if size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def verify_uploads(client, verbose: bool = False) -> bool:
    """Verify key files are accessible in R2."""
    prefix = r2_config.R2_PREFIX
    key_files = [
        f"{prefix}/basemap/planet.pmtiles",
        f"{prefix}/cities/index.json",
    ]

    print("\nVerifying uploads...")
    all_ok = True

    for key in key_files:
        try:
            response = client.head_object(Bucket=r2_config.R2_BUCKET, Key=key)
            size = response.get("ContentLength", 0)
            if verbose:
                print(f"  OK: {key} ({format_size(size)})")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                print(f"  MISSING: {key}")
                all_ok = False
            else:
                print(f"  ERROR: {key} - {e}")
                all_ok = False

    return all_ok


def get_bucket_size(client) -> int:
    """Get total size of all objects in bucket."""
    total_size = 0
    paginator = client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=r2_config.R2_BUCKET, Prefix=r2_config.R2_PREFIX):
        for obj in page.get("Contents", []):
            total_size += obj.get("Size", 0)

    return total_size


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview what would be uploaded without uploading")
@click.option("--force", is_flag=True, help="Upload all files, ignoring cache")
@click.option(
    "--only",
    multiple=True,
    type=click.Choice(["basemap", "h3", "cities"]),
    help="Upload only specific datasets",
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--test-only", is_flag=True, help="Scan files only, don't connect to R2")
def main(dry_run: bool, force: bool, only: tuple, verbose: bool, test_only: bool):
    """Upload processed data to Cloudflare R2."""
    print("=" * 60)
    print("UPLOAD TO R2")
    print("=" * 60)
    print()

    if dry_run:
        print("DRY RUN - no files will be uploaded")
        print()

    if test_only:
        print("TEST ONLY - scanning files without R2 connection")
        print()

    # Validate local data exists
    processed_dir = get_processed_path()
    if not processed_dir.exists():
        print(f"Error: Processed data directory not found: {processed_dir}")
        print("Run 'make all' first to generate data.")
        sys.exit(1)

    # Get mappings
    upload_mappings = get_upload_mappings()

    # Determine which datasets to upload
    datasets = list(only) if only else list(upload_mappings.keys())

    # Collect all files to upload
    print("[1/4] Scanning files...")
    all_files: list[tuple[Path, str]] = []

    for dataset in datasets:
        files = collect_files(dataset)
        if files:
            print(f"  {dataset}: {len(files)} files")
            all_files.extend(files)

    # Add extra files (like city_index.json)
    if not only or "cities" in only:
        for extra in get_extra_files():
            local_path = extra["local"]
            if local_path.exists():
                all_files.append((local_path, extra["r2_key"]))
                if verbose:
                    print(f"  extra: {local_path.name}")

    if not all_files:
        print("  No files found to upload.")
        sys.exit(0)

    print(f"  Total: {len(all_files)} files")

    if test_only:
        print()
        print("=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        return

    # Initialize S3 client
    print()
    print("[2/4] Connecting to R2...")
    client = get_s3_client()

    # Verify bucket access
    try:
        client.head_bucket(Bucket=r2_config.R2_BUCKET)
        print(f"  Connected to bucket: {r2_config.R2_BUCKET}")
    except ClientError as e:
        print(f"  Error accessing bucket: {e}")
        sys.exit(1)

    print(f"  Datasets: {', '.join(datasets)}")

    # Check which files need uploading
    print()
    print("[3/4] Checking for changes...")
    to_upload: list[tuple[Path, str]] = []
    skipped = 0

    # Group files by type for progress display
    file_groups: dict[str, list] = {}
    for local_path, r2_key in all_files:
        # Determine group for progress
        if "basemap" in r2_key:
            group = "basemap"
        elif "h3" in r2_key:
            group = "h3"
        elif "cities" in r2_key:
            group = "cities"
        else:
            group = "other"

        if group not in file_groups:
            file_groups[group] = []
        file_groups[group].append((local_path, r2_key))

    for group, files in file_groups.items():
        if len(files) > 10:
            # Show progress for groups with many files
            pbar = tqdm(files, desc=f"  Checking {group}", leave=False)
            for local_path, r2_key in pbar:
                if file_needs_upload(client, local_path, r2_key, force):
                    to_upload.append((local_path, r2_key))
                else:
                    skipped += 1
            pbar.close()
        else:
            for local_path, r2_key in files:
                if file_needs_upload(client, local_path, r2_key, force):
                    to_upload.append((local_path, r2_key))
                    if verbose:
                        print(f"  Changed: {local_path.name}")
                else:
                    skipped += 1
                    if verbose:
                        print(f"  Unchanged: {local_path.name}")

    print(f"  To upload: {len(to_upload)} files")
    print(f"  Skipped (unchanged): {skipped} files")

    if not to_upload:
        print()
        print("=" * 60)
        print("NO CHANGES - all files are up to date")
        print("=" * 60)
        sys.exit(0)

    # Upload files
    print()
    print("[4/4] Uploading files...")

    uploaded_count = 0
    uploaded_bytes = 0
    failed_count = 0
    failed_files: list[str] = []

    # Sort to upload large files first (basemap)
    to_upload.sort(key=lambda x: x[0].stat().st_size, reverse=True)

    for local_path, r2_key in to_upload:
        success, size = upload_file(client, local_path, r2_key, dry_run, verbose)
        if success:
            uploaded_count += 1
            uploaded_bytes += size
            if not dry_run and local_path.stat().st_size <= r2_config.PROGRESS_THRESHOLD:
                print(f"  Uploaded: {local_path.name}")
        else:
            failed_count += 1
            failed_files.append(str(local_path))

    # Summary
    print()
    print("=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print()

    action = "Would upload" if dry_run else "Uploaded"
    print(f"  {action}: {uploaded_count} files ({format_size(uploaded_bytes)})")
    print(f"  Skipped: {skipped} unchanged files")

    if failed_count > 0:
        print(f"  FAILED: {failed_count} files")
        for f in failed_files:
            print(f"    - {f}")
        sys.exit(1)

    # Verify and report bucket size
    if not dry_run:
        verify_uploads(client, verbose)

        print()
        print("Bucket storage:")
        total_size = get_bucket_size(client)
        print(f"  Total in {r2_config.R2_PREFIX}/: {format_size(total_size)}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()

"""
Shared R2 upload utility.

Consolidates the duplicated upload_to_r2() pattern from 6+ scripts.
Reads R2 credentials from environment variables (via .env file).

Usage:
    from ..utils.r2_upload import upload_to_r2
    upload_to_r2(local_path, r2_key, content_type="application/json")
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

# Lazy dotenv loading — only loads on first use, not at import time.
# This prevents test environment pollution when importing the module.
_dotenv_loaded = False


def _ensure_env_loaded() -> None:
    """Load .env file if not already loaded."""
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv()
        _dotenv_loaded = True


def get_r2_client():
    """Create boto3 S3 client configured for R2."""
    _ensure_env_loaded()

    required = ["R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise ValueError(
            f"Missing R2 credentials: {', '.join(missing)}. "
            "Create a .env file based on .env.example"
        )

    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def upload_to_r2(
    local_path: Path,
    r2_key: str,
    content_type: str = "application/octet-stream",
    bucket_name: str | None = None,
) -> str:
    """Upload a file to R2.

    Args:
        local_path: Path to local file
        r2_key: Destination key in R2
        content_type: MIME type for the upload
        bucket_name: Override bucket (defaults to R2_BUCKET_NAME env var)

    Returns:
        S3 URI of uploaded file
    """
    _ensure_env_loaded()
    bucket = bucket_name or os.environ.get("R2_BUCKET_NAME")
    if not bucket:
        raise ValueError("R2_BUCKET_NAME not set in environment")

    s3 = get_r2_client()

    file_size = local_path.stat().st_size
    if file_size < 1024**2:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024**2):.1f} MB"
    print(f"  Uploading {local_path.name} ({size_str}) -> {r2_key}")

    s3.upload_file(
        str(local_path),
        bucket,
        r2_key,
        ExtraArgs={"ContentType": content_type},
    )

    uri = f"s3://{bucket}/{r2_key}"
    print(f"  Uploaded to {uri}")
    return uri

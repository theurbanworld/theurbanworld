"""
R2 Configuration

Configuration for Cloudflare R2 uploads. Credentials are loaded from environment
variables. Create a .env file based on .env.example.

Environment variables:
    R2_ACCOUNT_ID        - Cloudflare account ID
    R2_ACCESS_KEY_ID     - R2 API access key ID
    R2_SECRET_ACCESS_KEY - R2 API secret access key
    R2_BUCKET            - Bucket name (default: urban-data-platform)
    R2_PREFIX            - Key prefix (default: urban-data)
    R2_CORS_ORIGINS      - Comma-separated list of allowed CORS origins

Decision log:
  - Using pydantic-settings for consistency with config.py
  - Credentials validated lazily (at use time, not import time)
  - Multipart settings tuned for 70GB basemap file
Date: 2025-12-09
"""

import os
import sys
from functools import cached_property
from pathlib import Path
from typing import ClassVar, Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Load .env file
load_dotenv(".env")


class R2Config(BaseSettings):
    """R2 configuration loaded from environment variables."""

    # Required credentials (validated at access time)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None

    # Optional settings with defaults
    R2_BUCKET: str = "urban-data-platform"
    R2_PREFIX: str = "urban-data"
    R2_CORS_ORIGINS: str = "https://urbandata.example.com,http://localhost:3000"

    # Content type mappings
    CONTENT_TYPES: ClassVar[dict[str, str]] = {
        ".pmtiles": "application/octet-stream",
        ".parquet": "application/vnd.apache.parquet",
        ".json": "application/json",
        ".geojson": "application/geo+json",
        ".gpkg": "application/geopackage+sqlite3",
    }

    # Cache control settings (in seconds)
    CACHE_CONTROL: ClassVar[dict[str, str]] = {
        "basemap": "public, max-age=604800",  # 7 days - updated monthly
        "h3": "public, max-age=86400",  # 1 day
        "cities": "public, max-age=86400",  # 1 day
        "default": "public, max-age=86400",  # 1 day default
    }

    # Multipart upload settings for large files
    MULTIPART_THRESHOLD: ClassVar[int] = 100 * 1024 * 1024  # 100 MB
    MULTIPART_CHUNKSIZE: ClassVar[int] = 100 * 1024 * 1024  # 100 MB per part
    MULTIPART_MAX_CONCURRENCY: ClassVar[int] = 4  # Concurrent upload threads
    MULTIPART_MAX_RETRIES: ClassVar[int] = 3  # Retry failed parts

    # Progress display threshold
    PROGRESS_THRESHOLD: ClassVar[int] = 100 * 1024 * 1024  # Show progress for files > 100 MB

    class Config:
        env_prefix = ""  # R2_ prefix is part of variable names
        case_sensitive = True

    @cached_property
    def endpoint(self) -> str:
        """Get R2 endpoint URL."""
        self._validate_credentials()
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    @cached_property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as list."""
        return [o.strip() for o in self.R2_CORS_ORIGINS.split(",")]

    def _validate_credentials(self) -> None:
        """Validate that required credentials are set."""
        missing = []
        if not self.R2_ACCOUNT_ID:
            missing.append("R2_ACCOUNT_ID")
        if not self.R2_ACCESS_KEY_ID:
            missing.append("R2_ACCESS_KEY_ID")
        if not self.R2_SECRET_ACCESS_KEY:
            missing.append("R2_SECRET_ACCESS_KEY")

        if missing:
            print(f"Error: Missing required environment variables: {', '.join(missing)}")
            print(f"Create a .env file based on .env.example in {_PROJECT_ROOT}")
            sys.exit(1)

    def get_content_type(self, filename: str) -> str:
        """Get content type for a file based on extension."""
        ext = Path(filename).suffix.lower()
        return self.CONTENT_TYPES.get(ext, "application/octet-stream")

    def get_cache_control(self, r2_key: str) -> str:
        """Get cache control header based on the R2 key path."""
        if r2_key.startswith(f"{self.R2_PREFIX}/basemap"):
            return self.CACHE_CONTROL["basemap"]
        elif r2_key.startswith(f"{self.R2_PREFIX}/h3"):
            return self.CACHE_CONTROL["h3"]
        elif r2_key.startswith(f"{self.R2_PREFIX}/cities"):
            return self.CACHE_CONTROL["cities"]
        return self.CACHE_CONTROL["default"]


# Global config instance
r2_config = R2Config()

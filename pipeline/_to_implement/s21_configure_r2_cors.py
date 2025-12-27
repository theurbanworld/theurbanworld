"""
21 - Configure R2 CORS

Purpose: Set up CORS policy on R2 bucket for browser access
Input: R2 credentials from environment
Output: CORS configuration applied to R2 bucket

This script configures CORS to allow:
  - GET, HEAD requests from configured origins
  - Range headers (required for PMTiles and Parquet byte-range requests)
  - Localhost access for development

Decision log:
  - Run this once after creating the R2 bucket
  - Range headers required for PMTiles and Parquet byte-range requests
  - 24-hour max age for CORS preflight caching
Date: 2024-12-09
"""

import sys

import boto3
import click
from botocore.exceptions import ClientError

from .utils.r2_config import r2_config


def get_s3_client():
    """Create boto3 S3 client configured for R2."""
    return boto3.client(
        "s3",
        endpoint_url=r2_config.endpoint,
        aws_access_key_id=r2_config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=r2_config.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


@click.command()
@click.option("--test-only", is_flag=True, help="Show current CORS config without modifying")
def main(test_only: bool = False):
    """Configure CORS on the R2 bucket for browser access."""
    print("=" * 60)
    print("CONFIGURE R2 CORS")
    print("=" * 60)
    print()

    client = get_s3_client()

    # CORS configuration for PMTiles and Parquet access
    cors_config = {
        "CORSRules": [
            {
                "AllowedOrigins": r2_config.cors_origins,
                "AllowedMethods": ["GET", "HEAD"],
                "AllowedHeaders": ["Range", "Content-Type"],
                "ExposeHeaders": ["Content-Range", "Content-Length", "Accept-Ranges"],
                "MaxAgeSeconds": 86400,  # 24 hours
            }
        ]
    }

    print("CORS Configuration:")
    print(f"  Bucket: {r2_config.R2_BUCKET}")
    print(f"  Allowed Origins: {', '.join(r2_config.cors_origins)}")
    print("  Allowed Methods: GET, HEAD")
    print("  Allowed Headers: Range, Content-Type")
    print("  Exposed Headers: Content-Range, Content-Length, Accept-Ranges")
    print("  Max Age: 86400 seconds (24 hours)")
    print()

    try:
        # Check bucket exists first
        print("[1/3] Verifying bucket access...")
        client.head_bucket(Bucket=r2_config.R2_BUCKET)
        print(f"  Bucket '{r2_config.R2_BUCKET}' is accessible.")

        if test_only:
            # Just show current config
            print()
            print("[2/3] Reading current CORS configuration...")
            try:
                response = client.get_bucket_cors(Bucket=r2_config.R2_BUCKET)
                rules = response.get("CORSRules", [])
                if rules:
                    print(f"  Found {len(rules)} CORS rule(s):")
                    for i, rule in enumerate(rules, 1):
                        origins = rule.get("AllowedOrigins", [])
                        methods = rule.get("AllowedMethods", [])
                        print(f"    Rule {i}: {len(origins)} origin(s), methods: {', '.join(methods)}")
                        for origin in origins:
                            print(f"      - {origin}")
                else:
                    print("  No CORS rules configured.")
            except ClientError as e:
                if "NoSuchCORSConfiguration" in str(e):
                    print("  No CORS configuration found.")
                else:
                    raise
            print()
            print("=" * 60)
            print("TEST COMPLETE - no changes made")
            print("=" * 60)
            return

        # Apply CORS configuration
        print()
        print("[2/3] Applying CORS configuration...")
        client.put_bucket_cors(Bucket=r2_config.R2_BUCKET, CORSConfiguration=cors_config)
        print("  CORS configuration applied successfully.")

        # Verify by reading it back
        print()
        print("[3/3] Verifying configuration...")
        response = client.get_bucket_cors(Bucket=r2_config.R2_BUCKET)
        rules = response.get("CORSRules", [])

        if rules:
            print(f"  Verified: {len(rules)} CORS rule(s) configured")
            for i, rule in enumerate(rules, 1):
                origins = rule.get("AllowedOrigins", [])
                methods = rule.get("AllowedMethods", [])
                print(f"    Rule {i}: {len(origins)} origin(s), methods: {', '.join(methods)}")
        else:
            print("  Warning: No CORS rules found after configuration")

        print()
        print("=" * 60)
        print("CORS CONFIGURATION COMPLETE")
        print("=" * 60)
        print()
        print("Your R2 bucket is now configured for browser access.")
        print("PMTiles and Parquet files can be loaded directly from the browser.")
        print()
        print("To update allowed origins, set R2_CORS_ORIGINS in your .env file:")
        print("  R2_CORS_ORIGINS=https://your-domain.com,http://localhost:3000")
        print()

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))

        print(f"Error: {error_code}")
        print(f"  {error_msg}")
        print()

        if error_code == "NoSuchBucket":
            print(f"The bucket '{r2_config.R2_BUCKET}' does not exist.")
            print("Create it in the Cloudflare dashboard first.")
        elif error_code == "AccessDenied":
            print("Access denied. Check your R2 API credentials.")
            print("Ensure your API token has permission to manage bucket CORS.")

        sys.exit(1)


if __name__ == "__main__":
    main()

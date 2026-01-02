"""
Generate MapLibre-compatible font glyphs for Inter and Crimson Pro fonts.

Purpose: Download font files from GitHub/Google Fonts, generate SDF (Signed Distance
         Field) PBF glyphs using build_pbf_glyphs, and upload to R2 for use with
         MapLibre GL city labels.

Usage:
  uv run python -m src.s10_generate_font_glyphs           # Generate and upload
  uv run python -m src.s10_generate_font_glyphs --local   # Generate only (no upload)

Requirements:
  - build_pbf_glyphs installed (cargo install build_pbf_glyphs)
  - FreeType 2.10+ available
  - R2 credentials in .env

Date: 2026-01-02
"""

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
OUTPUT_DIR = Path("data/processed/fonts")
R2_PREFIX = "fonts"

# Font families to generate
# "type": "zip" = download zip and extract, "type": "direct" = download individual TTF files
FONT_FAMILIES = {
    "Inter": {
        "type": "zip",
        "url": "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip",
        "variants": {
            "Inter Regular": "Inter-Regular.ttf",
            "Inter Medium": "Inter-Medium.ttf",
            "Inter Bold": "Inter-Bold.ttf",
        }
    },
    "Crimson Pro": {
        "type": "direct",
        "variants": {
            "Crimson Pro Regular": "https://cdn.jsdelivr.net/fontsource/fonts/crimson-pro@latest/latin-400-normal.ttf",
            "Crimson Pro SemiBold": "https://cdn.jsdelivr.net/fontsource/fonts/crimson-pro@latest/latin-600-normal.ttf",
            "Crimson Pro Bold": "https://cdn.jsdelivr.net/fontsource/fonts/crimson-pro@latest/latin-700-normal.ttf",
        }
    }
}


def check_prerequisites() -> None:
    """Verify required tools are installed."""
    print("Checking prerequisites...")

    # Check build_pbf_glyphs
    result = subprocess.run(
        ["which", "build_pbf_glyphs"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            "build_pbf_glyphs not found. Install with: cargo install build_pbf_glyphs"
        )
    print(f"  build_pbf_glyphs: {result.stdout.strip()}")

    # Check FreeType (via pkg-config)
    result = subprocess.run(
        ["pkg-config", "--modversion", "freetype2"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("  Warning: Could not verify FreeType version (pkg-config failed)")
    else:
        version = result.stdout.strip()
        print(f"  FreeType: {version}")


def download_font_family(family_name: str, family_config: dict, output_dir: Path) -> dict[str, Path]:
    """Download font files for a font family.

    Supports two download types:
    - "zip": Download a zip file and extract specific TTF files
    - "direct": Download individual TTF files directly from URLs

    Args:
        family_name: Display name of the font family (e.g., "Inter", "Crimson Pro")
        family_config: Dict with "type", "variants", and optionally "url" keys
        output_dir: Directory to download/extract fonts to

    Returns:
        Dict mapping MapLibre font name to local TTF path
    """
    print(f"\nDownloading {family_name} fonts...")
    output_dir.mkdir(parents=True, exist_ok=True)

    download_type = family_config.get("type", "zip")
    variants = family_config["variants"]
    font_paths = {}

    if download_type == "direct":
        # Download individual TTF files directly
        for maplibre_name, url in variants.items():
            print(f"  Fetching {maplibre_name}...")
            response = requests.get(url)
            response.raise_for_status()

            dest_path = output_dir / f"{maplibre_name}.ttf"
            dest_path.write_bytes(response.content)

            font_paths[maplibre_name] = dest_path
            file_size = dest_path.stat().st_size / 1024
            print(f"    Saved {dest_path.name} ({file_size:.1f} KB)")

    else:  # zip
        url = family_config["url"]

        # Download the release zip
        print(f"  Fetching {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        zip_path = output_dir / f"{family_name.lower().replace(' ', '_')}.zip"
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        zip_size = zip_path.stat().st_size / 1024 / 1024
        print(f"  Downloaded {zip_size:.1f} MB")

        # Extract the zip
        print("  Extracting...")
        extract_dir = output_dir / f"{family_name.lower().replace(' ', '_')}_extract"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Find the TTF files we need
        for maplibre_name, ttf_filename in variants.items():
            # Search for the TTF file in extracted contents
            matches = list(extract_dir.rglob(ttf_filename))
            if not matches:
                # Try case-insensitive search
                matches = [p for p in extract_dir.rglob("*.ttf") if p.name.lower() == ttf_filename.lower()]
            if not matches:
                # List available files for debugging
                all_ttf = list(extract_dir.rglob("*.ttf"))
                print(f"  Available TTF files: {[f.name for f in all_ttf[:10]]}")
                raise RuntimeError(f"Could not find {ttf_filename} in {family_name} archive")

            # Use the first match
            source_path = matches[0]

            # Copy to output with MapLibre-compatible name
            # build_pbf_glyphs uses the filename (without extension) as the output folder name
            dest_path = output_dir / f"{maplibre_name}.ttf"
            shutil.copy(source_path, dest_path)

            font_paths[maplibre_name] = dest_path
            print(f"  Found {maplibre_name}: {source_path.name}")

        # Clean up zip and extracted folders
        zip_path.unlink()
        shutil.rmtree(extract_dir)

    return font_paths


def generate_pbf_glyphs(font_dir: Path, output_dir: Path) -> None:
    """Generate PBF glyphs using build_pbf_glyphs.

    The tool expects:
      build_pbf_glyphs <input_directory> <output_directory>

    It creates output_directory/<font_name>/0-255.pbf, etc.
    where font_name is derived from the TTF filename.

    Args:
        font_dir: Directory containing TTF files
        output_dir: Directory to write PBF files
    """
    print("\nGenerating PBF glyphs...")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run build_pbf_glyphs on the font directory
    cmd = [
        "build_pbf_glyphs",
        str(font_dir),
        str(output_dir)
    ]

    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
        raise RuntimeError(f"build_pbf_glyphs failed: {result.stderr}")

    print(f"  stdout: {result.stdout.strip()}")

    # Count generated files per variant
    for variant_dir in sorted(output_dir.iterdir()):
        if variant_dir.is_dir():
            pbf_files = list(variant_dir.glob("*.pbf"))
            print(f"  {variant_dir.name}: {len(pbf_files)} PBF files")


def upload_fonts_to_r2(fonts_dir: Path) -> int:
    """Upload all font PBF files to R2.

    Args:
        fonts_dir: Directory containing font variant subdirectories

    Returns:
        Number of files uploaded
    """
    print("\nUploading fonts to R2...")

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

    uploaded_count = 0

    # Iterate through font variant directories
    for variant_dir in sorted(fonts_dir.iterdir()):
        if not variant_dir.is_dir():
            continue

        variant_name = variant_dir.name
        print(f"  Uploading {variant_name}...")

        # Upload each PBF file
        pbf_files = list(variant_dir.glob("*.pbf"))
        for pbf_file in pbf_files:
            r2_key = f"{R2_PREFIX}/{variant_name}/{pbf_file.name}"

            s3.upload_file(
                str(pbf_file),
                bucket_name,
                r2_key,
                ExtraArgs={
                    "ContentType": "application/x-protobuf",
                    "CacheControl": "public, max-age=31536000",  # 1 year (fonts rarely change)
                }
            )
            uploaded_count += 1

        print(f"    Uploaded {len(pbf_files)} files")

    print(f"\nTotal uploaded: {uploaded_count} files")
    return uploaded_count


def main(local_only: bool = False) -> None:
    """Generate font glyphs for all font families and upload to R2."""
    print("=" * 60)
    print("Font Glyph Generator (Inter + Crimson Pro)")
    print("=" * 60)

    # Check prerequisites
    check_prerequisites()

    # Use temp directory for downloaded fonts
    with tempfile.TemporaryDirectory() as tmpdir:
        download_dir = Path(tmpdir)

        # Download all font families
        for family_name, family_config in FONT_FAMILIES.items():
            download_font_family(family_name, family_config, download_dir)

        # List TTF files in download dir
        ttf_files = list(download_dir.glob("*.ttf"))
        print(f"\nFont files ready for processing: {len(ttf_files)}")
        for ttf in sorted(ttf_files):
            print(f"  {ttf.name}")

        # Generate PBF glyphs for all fonts
        generate_pbf_glyphs(download_dir, OUTPUT_DIR)

    # Print output summary
    print("\nGenerated font glyphs:")
    for variant_dir in sorted(OUTPUT_DIR.iterdir()):
        if variant_dir.is_dir():
            pbf_count = len(list(variant_dir.glob("*.pbf")))
            print(f"  {variant_dir.name}: {pbf_count} files")

    # Upload to R2
    if not local_only:
        upload_fonts_to_r2(OUTPUT_DIR)
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_DIR}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate font glyphs for MapLibre")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

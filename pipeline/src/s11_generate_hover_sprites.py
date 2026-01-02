"""
Generate MapLibre-compatible sprite sheet for city hover patterns.

Purpose: Create diagonal stripe patterns for Paradox-style hover effects on city
         boundaries. Generates sprite sheet PNG and JSON metadata for MapLibre GL.

Usage:
  uv run python -m src.s11_generate_hover_sprites           # Generate and upload
  uv run python -m src.s11_generate_hover_sprites --local   # Generate only (no upload)

Requirements:
  - Pillow for image generation
  - R2 credentials in .env

Date: 2026-01-02
"""

import json
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv
from PIL import Image, ImageDraw

# Load environment variables
load_dotenv()

# Constants
OUTPUT_DIR = Path("data/processed/sprites")
R2_PREFIX = "sprites"

# Color palette (matches useMap.ts boundary colors)
# Each pattern needs light variant for the stripe itself
PATTERNS = {
    "diagonal-0": "#D4B896",  # Warm tan
    "diagonal-1": "#96B8D4",  # Slate blue
    "diagonal-2": "#B8D496",  # Sage green
    "diagonal-3": "#D496B8",  # Dusty rose
    "diagonal-4": "#96D4B8",  # Seafoam
    "diagonal-5": "#B896D4",  # Lavender
}

# Sprite size (must be power of 2 for WebGL efficiency)
SPRITE_SIZE = 16  # 16x16 for crisp diagonal lines


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert hex color to RGBA tuple."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b, alpha)


def create_diagonal_pattern(color: str, size: int = SPRITE_SIZE) -> Image.Image:
    """Create a diagonal stripe pattern image.

    Creates thin diagonal lines going from bottom-left to top-right,
    similar to Paradox Interactive occupation patterns.
    """
    # Create transparent image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Get color with ~60% opacity for the stripes
    rgba = hex_to_rgba(color, alpha=153)  # 60% of 255

    # Draw diagonal lines (bottom-left to top-right)
    # Line width of 2px, spaced 6px apart for 16x16 sprite
    line_width = 2
    spacing = 6

    # Draw lines extending beyond the sprite to ensure full coverage
    for offset in range(-size * 2, size * 2, spacing):
        # Line from (offset, size) to (offset + size, 0)
        draw.line(
            [(offset, size), (offset + size, 0)],
            fill=rgba,
            width=line_width
        )

    return img


def generate_sprite_sheet(pixel_ratio: int = 1) -> tuple[Image.Image, dict]:
    """Generate sprite sheet image and JSON metadata.

    Args:
        pixel_ratio: 1 for standard displays, 2 for retina/high-DPI

    Returns:
        Tuple of (sprite_sheet_image, metadata_dict)
    """
    print(f"Generating sprite patterns ({pixel_ratio}x)...")

    # Scale sprite size for high-DPI
    scaled_size = SPRITE_SIZE * pixel_ratio

    # Calculate sprite sheet dimensions
    # Arrange sprites in a row for simplicity
    num_patterns = len(PATTERNS)
    sheet_width = scaled_size * num_patterns
    sheet_height = scaled_size

    # Create sprite sheet
    sprite_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    # Metadata for MapLibre
    metadata = {}

    # Generate each pattern
    for i, (name, color) in enumerate(PATTERNS.items()):
        print(f"  Creating {name} ({color})...")

        # Create pattern at scaled size
        pattern = create_diagonal_pattern(color, size=scaled_size)

        # Paste into sprite sheet
        x = i * scaled_size
        y = 0
        sprite_sheet.paste(pattern, (x, y))

        # Add metadata (MapLibre sprite format)
        # Note: coordinates are in actual pixels, but width/height are logical
        metadata[name] = {
            "x": x,
            "y": y,
            "width": scaled_size,
            "height": scaled_size,
            "pixelRatio": pixel_ratio
        }

    return sprite_sheet, metadata


def save_sprites(sprite_sheet: Image.Image, metadata: dict, suffix: str = "") -> tuple[Path, Path]:
    """Save sprite sheet and metadata to local files.

    Args:
        sprite_sheet: The sprite sheet image
        metadata: The sprite metadata dict
        suffix: Optional suffix (e.g., "@2x" for retina)

    Returns:
        Tuple of (png_path, json_path)
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    png_path = OUTPUT_DIR / f"patterns{suffix}.png"
    json_path = OUTPUT_DIR / f"patterns{suffix}.json"

    # Save PNG
    sprite_sheet.save(png_path, "PNG")
    print(f"  Saved {png_path} ({png_path.stat().st_size} bytes)")

    # Save JSON
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved {json_path}")

    return png_path, json_path


def upload_sprites_to_r2(files: list[tuple[Path, Path]]) -> None:
    """Upload sprite sheets and metadata to R2.

    Args:
        files: List of (png_path, json_path) tuples
    """
    print("\nUploading sprites to R2...")

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

    for png_path, json_path in files:
        # Upload PNG
        png_key = f"{R2_PREFIX}/{png_path.name}"
        s3.upload_file(
            str(png_path),
            bucket_name,
            png_key,
            ExtraArgs={
                "ContentType": "image/png",
                "CacheControl": "public, max-age=31536000",  # 1 year
            }
        )
        print(f"  Uploaded {png_key}")

        # Upload JSON
        json_key = f"{R2_PREFIX}/{json_path.name}"
        s3.upload_file(
            str(json_path),
            bucket_name,
            json_key,
            ExtraArgs={
                "ContentType": "application/json",
                "CacheControl": "public, max-age=31536000",  # 1 year
            }
        )
        print(f"  Uploaded {json_key}")

    print(f"\nSprites available at:")
    print(f"  https://data.theurban.world/sprites/patterns.png")
    print(f"  https://data.theurban.world/sprites/patterns@2x.png")


def main(local_only: bool = False) -> None:
    """Generate hover pattern sprites and upload to R2."""
    print("=" * 60)
    print("Hover Pattern Sprite Generator")
    print("=" * 60)

    # Generate both 1x and 2x sprite sheets
    files = []

    # 1x (standard displays)
    sprite_sheet_1x, metadata_1x = generate_sprite_sheet(pixel_ratio=1)
    print("\nSaving 1x sprite files...")
    files.append(save_sprites(sprite_sheet_1x, metadata_1x, suffix=""))

    # 2x (retina/high-DPI displays)
    sprite_sheet_2x, metadata_2x = generate_sprite_sheet(pixel_ratio=2)
    print("\nSaving 2x sprite files...")
    files.append(save_sprites(sprite_sheet_2x, metadata_2x, suffix="@2x"))

    # Upload to R2
    if not local_only:
        upload_sprites_to_r2(files)
    else:
        print(f"\nLocal only mode - skipping R2 upload")
        print(f"Output: {OUTPUT_DIR}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate hover pattern sprites")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

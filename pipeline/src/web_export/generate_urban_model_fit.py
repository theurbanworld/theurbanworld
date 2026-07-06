"""
Generate Standard Urban Model fit JSON for the frontend.

Purpose: Convert radial_fits_h3_r8.parquet to compact nested JSON so the web app
         can overlay the fitted monocentric curve, derive compactness/structure
         labels, and surface D0/beta/R2 per city-epoch.

Output format: { city_id: { epoch: { D0, beta, r2, reliable, fitted } } }
  - D0/beta/r2: fitted parameters and goodness-of-fit (null when unfittable)
  - reliable: whether the fit meets the reliability criteria
  - fitted: model curve evaluated at each ring mid-distance (index = ring_index),
            rounded and trimmed at the last non-null; null when reliable=false so the
            web suppresses the dashed curve (honest-null, KTD4)

n_rings is validated in the parquet schema but intentionally omitted from this JSON.

Usage:
  uv run python -m src.web_export.generate_urban_model_fit           # Generate and upload
  uv run python -m src.web_export.generate_urban_model_fit --local   # Generate only

Date: 2026-06-27
"""

import json
import math
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ..utils.config import config

# Density rounding: 1 decimal, matching radial_profiles export. beta/r2 keep more
# precision since they are small numbers the labels/sorts depend on.
DENSITY_DECIMALS = 1
BETA_DECIMALS = 4
R2_DECIMALS = 3


def _round_or_none(value, decimals: int):
    """Round a value to `decimals`, returning None for null/NaN/non-finite."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, decimals)


def build_fitted_curve(
    d0: float, beta: float, num_rings: int, ring_width_km: float
) -> list[float | None]:
    """Evaluate D(r)=D0*e^(-beta*r) at each ring mid-distance, rounded and trimmed.

    Values that round to 0 become null; trailing nulls are trimmed to keep the
    payload small (mirrors the radial-profiles trailing-null convention).
    """
    curve: list[float | None] = []
    for ring_index in range(num_rings):
        r = (ring_index + 0.5) * ring_width_km
        value = round(float(d0 * math.exp(-beta * r)), DENSITY_DECIMALS)
        curve.append(None if value == 0 else value)

    while curve and curve[-1] is None:
        curve.pop()

    return curve


def load_fits(parquet_path: Path) -> pd.DataFrame:
    """Load exponential fits from parquet."""
    print(f"Loading exponential fits from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"  Loaded {len(df):,} city-epoch fits ({df['city_id'].nunique():,} cities)")
    return df


def generate_json(df: pd.DataFrame) -> dict:
    """Convert fits DataFrame to compact nested JSON.

    Output: { city_id: { epoch: { D0, beta, r2, reliable, fitted } } }
    """
    print("Generating nested JSON...")

    num_rings = config.RADIAL_NUM_RINGS
    ring_width = config.RADIAL_RING_WIDTH_KM

    cities: dict[str, dict[str, dict]] = defaultdict(dict)

    for row in df.itertuples(index=False):
        reliable = bool(row.reliable)
        d0 = _round_or_none(row.D0, DENSITY_DECIMALS)
        beta = _round_or_none(row.beta, BETA_DECIMALS)
        r2 = _round_or_none(row.r2, R2_DECIMALS)

        # Suppress the fitted curve when the fit is not reliable (honest-null).
        if reliable and row.D0 is not None and row.beta is not None and math.isfinite(
            float(row.D0)
        ) and math.isfinite(float(row.beta)):
            fitted = build_fitted_curve(float(row.D0), float(row.beta), num_rings, ring_width)
        else:
            fitted = None

        cities[str(row.city_id)][str(int(row.epoch))] = {
            "D0": d0,
            "beta": beta,
            "r2": r2,
            "reliable": reliable,
            "fitted": fitted,
        }

    print(f"  Generated {len(cities):,} city records")
    return dict(cities)


def save_json(data: dict, output_path: Path) -> None:
    """Save to compact JSON."""
    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    file_size = output_path.stat().st_size / 1e6
    print(f"  Saved {output_path} ({file_size:.1f} MB)")


def main(local_only: bool = False) -> None:
    """Generate urban model fit JSON and upload to R2."""
    print("=" * 60)
    print("Urban Model Fit JSON Generator")
    print("=" * 60)

    parquet_path = Path("data/processed/radial_profiles/radial_fits_h3_r8.parquet")
    output_json = Path("data/processed/tiles/urban_model_fit_h3_r8.json")
    r2_key = "data/urban_model_fit_h3_r8.json"

    df = load_fits(parquet_path)
    data = generate_json(df)
    save_json(data, output_json)

    if not local_only:
        from ..utils.r2_upload import upload_to_r2

        print()
        upload_to_r2(output_json, r2_key, content_type="application/json")
    else:
        print("\nLocal only mode - skipping R2 upload")
        print(f"Output: {output_json}")

    print("\nDone!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate urban model fit JSON")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

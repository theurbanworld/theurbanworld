"""Generate climate JSON for the frontend (summary + per-city profile).

Mirrors the governance/radial summary-vs-detail split:
  - climate_summary.json: Record<city_id, {<headline key>: number}>
      Only the headline-four latest values — lightweight for rankings and
      distribution strips. (R12)
  - climate_profile.json: Record<city_id, ClimateRecord>
      Full per-metric shapes for the city section. If it exceeds the split
      threshold, per-city files are written under tiles/climate/{city_id}.json
      (the generate_city_cells.py pattern).

Input:
  - data/processed/climate/city_climate.parquet
Output (under data/processed/tiles/, uploaded to R2 under data/):
  - climate_summary.json
  - climate_profile.json   (or climate/{city_id}.json per-city files)

Usage:
  uv run python -m src.web_export.generate_climate          # generate + upload
  uv run python -m src.web_export.generate_climate --local  # generate only

Date: 2026-06-27
"""

import json
from pathlib import Path

import polars as pl

from ..climate import catalog

# Flat parquet column -> headline metric key (web summary keys).
SUMMARY_COLUMNS = {
    "heat_warm_days_now": catalog.HEAT_HEADLINE_KEY,
    "flood_100yr_share_latest": catalog.FLOOD_HEADLINE_KEY,
    "solar_pv_potential": catalog.SOLAR_HEADLINE_KEY,
    "co2_per_capita_latest": catalog.CARBON_HEADLINE_KEY,
}

# Split climate_profile.json into per-city files above this size.
PROFILE_SPLIT_MB = 5.0


def _round(value):
    """Round numbers to 4 significant-ish decimals; pass through everything else."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, list):
        return [_round(v) for v in value]
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    return value


def build_summary(df: pl.DataFrame) -> dict:
    """{ city_id: { <headline key>: number } } — only non-null headline values."""
    summary: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        entry = {}
        for col, key in SUMMARY_COLUMNS.items():
            value = row.get(col)
            if value is not None:
                entry[key] = _round(float(value))
        if entry:
            summary[row["city_id"]] = entry
    return summary


def build_profile(df: pl.DataFrame) -> dict:
    """{ city_id: ClimateRecord } — full per-metric shapes, absent metrics omitted."""
    profile: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        record = json.loads(row["climate_json"])
        if record:
            profile[row["city_id"]] = _round(record)
    return profile


def _dump(data: dict) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def _upload_one(s3_client, bucket: str, local_path: Path, r2_key: str) -> str:
    """Upload a single JSON file to R2. Returns the r2_key on success."""
    s3_client.upload_file(
        str(local_path),
        bucket,
        r2_key,
        ExtraArgs={"ContentType": "application/json"},
    )
    return r2_key


def write_outputs(
    df: pl.DataFrame,
    out_dir: Path,
    split_threshold_mb: float = PROFILE_SPLIT_MB,
) -> dict:
    """Write summary + profile JSON. Returns a manifest of written paths + R2 keys.

    If the profile exceeds ``split_threshold_mb`` it is written per-city under
    ``out_dir/climate/{city_id}.json`` instead of a single file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(df)
    profile = build_profile(df)

    summary_path = out_dir / "climate_summary.json"
    summary_path.write_text(_dump(summary))

    profile_text = _dump(profile)
    profile_mb = len(profile_text.encode("utf-8")) / 1e6

    written: list[tuple[Path, str]] = [(summary_path, "data/climate_summary.json")]
    split = profile_mb > split_threshold_mb

    if not split:
        profile_path = out_dir / "climate_profile.json"
        profile_path.write_text(profile_text)
        written.append((profile_path, "data/climate_profile.json"))
    else:
        per_city_dir = out_dir / "climate"
        per_city_dir.mkdir(parents=True, exist_ok=True)
        for city_id, record in profile.items():
            city_path = per_city_dir / f"{city_id}.json"
            city_path.write_text(_dump(record))
            written.append((city_path, f"data/climate/{city_id}.json"))

    return {
        "summary": summary,
        "profile": profile,
        "profile_mb": profile_mb,
        "split": split,
        "written": written,
    }


def main(local_only: bool = False, split_threshold_mb: float = PROFILE_SPLIT_MB) -> None:
    """Generate climate JSON and upload to R2."""
    print("=" * 60)
    print("Climate JSON Generator")
    print("=" * 60)

    parquet_path = Path("data/processed/climate/city_climate.parquet")
    out_dir = Path("data/processed/tiles")

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {parquet_path}\n"
            "Run 'python -m src.climate.build_city_climate' first."
        )

    print(f"Loading {parquet_path}...")
    df = pl.read_parquet(parquet_path)
    print(f"  {len(df):,} cities with climate data")

    manifest = write_outputs(df, out_dir, split_threshold_mb)

    print(f"\n  Summary cities: {len(manifest['summary']):,}")
    print(f"  Profile cities: {len(manifest['profile']):,}")
    print(f"  Profile size: {manifest['profile_mb']:.2f} MB")
    if manifest["split"]:
        print(f"  Profile split into {len(manifest['written']) - 1:,} per-city files")

    if local_only:
        print("\nLocal only mode - skipping R2 upload")
        for path, _ in manifest["written"][:3]:
            print(f"  Output: {path}")
        return

    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ..utils.r2_upload import get_r2_client

    s3 = get_r2_client()
    bucket = os.environ.get("R2_BUCKET_NAME")
    if not bucket:
        raise ValueError("R2_BUCKET_NAME not set in environment")

    written = manifest["written"]
    print(f"\nUploading {len(written):,} files to R2 (20 threads)...")
    uploaded = 0
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {
            pool.submit(_upload_one, s3, bucket, path, r2_key): r2_key
            for path, r2_key in written
        }
        for future in as_completed(futures):
            future.result()  # raises on error
            uploaded += 1
            if uploaded % 1000 == 0 or uploaded == len(written):
                print(f"  {uploaded:,}/{len(written):,} uploaded")

    print(f"\nDone — {uploaded:,} files uploaded.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate climate JSON")
    parser.add_argument("--local", action="store_true", help="Skip R2 upload")
    args = parser.parse_args()

    main(local_only=args.local)

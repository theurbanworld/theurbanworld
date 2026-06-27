"""Build ``city_climate.parquet`` from already-extracted UCDB attributes.

Reshapes the climate metric catalog's attributes out of ``ucdb_all.parquet``
(interim) into a per-city climate table, preserving each metric's temporal
structure. No new download — this is the pipeline ceasing to discard data it
already holds.

Input:
  - data/interim/ucdb/ucdb_all.parquet  (all 15 themes, already extracted)
Output:
  - data/processed/climate/city_climate.parquet

Output Schema (city_climate.parquet — one row per city):
  | Column                    | Type   | Notes                                        |
  |---------------------------|--------|----------------------------------------------|
  | city_id                   | str    | ID_UC_G0, primary key (matches cities.parquet)|
  | heat_warm_days_now        | f64?   | headline heat — current warm days (TX90p)     |
  | flood_100yr_share_latest  | f64?   | headline flood — latest 100-yr flood share    |
  | solar_pv_potential        | f64?   | headline solar — PV potential (kWh/kWp)        |
  | co2_per_capita_latest     | f64?   | headline carbon — latest per-capita CO₂        |
  | wind_speed_100m           | f64?   | snapshot wind speed @100 m                     |
  | canopy_height             | f64?   | snapshot mean canopy height                    |
  | sea_level_rise            | f64?   | snapshot local SLR rate (signed)               |
  | heatwave_events           | i64?   | snapshot heatwave event count                  |
  | drought_events            | i64?   | snapshot drought event count                   |
  | climate_json              | str    | full per-metric ClimateRecord (JSON)           |

The flat headline/snapshot columns are the validatable + summary surface
(U3 Pandera, U4 ``climate_summary.json``). ``climate_json`` is the full reshape
(U4 ``climate_profile.json``). Per-metric NULLs are legitimate partial coverage;
a city with no climate attributes at all is dropped (it renders the unavailable
state via absence). Web mirror: ``web/types/climate.ts``.

Decision log:
  - ID_UC_G0 -> city_id (str), consistent with generate_cities.py
  - Reshape by temporal class: series -> ordered points; projection -> now/future;
    snapshot -> scalar / composition / sector fingerprint
  - climate_json omits absent metrics (keys, not nulls) so the profile stays small
Date: 2026-06-27
"""

import json

import click
import polars as pl

from ..utils.config import get_interim_path, get_processed_path
from . import catalog
from .catalog import Metric, TemporalClass

# Local Climate Zone class labels (CL_LCZ_A01..A17), in attribute order.
LCZ_LABELS = (
    "Compact high-rise",
    "Compact mid-rise",
    "Compact low-rise",
    "Open high-rise",
    "Open mid-rise",
    "Open low-rise",
    "Lightweight low-rise",
    "Large low-rise",
    "Sparsely built",
    "Heavy industry",
    "Dense trees",
    "Scattered trees",
    "Bush, scrub",
    "Low plants",
    "Bare rock/paved",
    "Bare soil/sand",
    "Water",
)


def _num(value: object) -> float | None:
    """Coerce a cell to float, treating NaN/None as absent."""
    if value is None:
        return None
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _year_of(col: str) -> int | None:
    tail = col.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else None


def reshape_metric(metric: Metric, row: dict) -> dict | None:
    """Reshape one metric's attributes for one city. Returns None if absent.

    Shapes (read on the web side by temporal class):
      series      -> {"points": [[year, value], ...]}            (ascending year)
      projection  -> {"now": value|null, "future": value|null}   (categorical ok)
      snapshot    -> {"value": number}
      composition -> {"parts": [[label, value], ...]}            (LCZ)
      fingerprint -> {"sectors": [[label, value], ...]}          (CO₂ sectors)
    """
    if metric.sector_fingerprint:
        sectors = [
            [label, _num(row.get(col))]
            for label, col in zip(metric.sector_labels, metric.ucdb_attribute_ids)
        ]
        sectors = [s for s in sectors if s[1] is not None]
        return {"sectors": sectors} if sectors else None

    if metric.temporal_class is TemporalClass.SERIES:
        points = []
        for col in metric.ucdb_attribute_ids:
            year = _year_of(col)
            value = _num(row.get(col))
            if year is not None and value is not None:
                points.append([year, value])
        points.sort(key=lambda p: p[0])
        return {"points": points} if points else None

    if metric.temporal_class is TemporalClass.PROJECTION:
        now_col, future_col = metric.ucdb_attribute_ids
        if metric.categorical:
            now = row.get(now_col)
            future = row.get(future_col)
            now = str(now) if now not in (None, "") else None
            future = str(future) if future not in (None, "") else None
        else:
            now = _num(row.get(now_col))
            future = _num(row.get(future_col))
        if now is None and future is None:
            return None
        return {"now": now, "future": future}

    # SNAPSHOT
    if len(metric.ucdb_attribute_ids) == 1:
        value = _num(row.get(metric.ucdb_attribute_ids[0]))
        return {"value": value} if value is not None else None

    # SNAPSHOT composition (e.g. LCZ): multiple columns -> labelled parts
    labels = LCZ_LABELS if metric.key == "lcz_composition" else metric.ucdb_attribute_ids
    parts = [
        [label, _num(row.get(col))]
        for label, col in zip(labels, metric.ucdb_attribute_ids)
    ]
    parts = [p for p in parts if p[1] is not None]
    return {"parts": parts} if parts else None


def build_record(row: dict) -> dict:
    """Build the full ClimateRecord (metric key -> shape) for a city.

    Absent metrics are omitted (keys, not nulls), so partial coverage serializes
    only the metrics the city has.
    """
    record: dict[str, dict] = {}
    for metric in catalog.metrics():
        shape = reshape_metric(metric, row)
        if shape is not None:
            record[metric.key] = shape
    return record


def _latest_series_value(shape: dict | None) -> float | None:
    if not shape or not shape.get("points"):
        return None
    return shape["points"][-1][1]


def extract_headline_scalars(record: dict) -> dict:
    """Pull the flat headline + snapshot scalars used for summary/rankings/validation."""
    warm = record.get(catalog.HEAT_HEADLINE_KEY)
    return {
        "heat_warm_days_now": _num(warm.get("now")) if warm else None,
        "flood_100yr_share_latest": _latest_series_value(record.get(catalog.FLOOD_HEADLINE_KEY)),
        "solar_pv_potential": (
            record.get(catalog.SOLAR_HEADLINE_KEY, {}).get("value")
            if catalog.SOLAR_HEADLINE_KEY in record
            else None
        ),
        "co2_per_capita_latest": _latest_series_value(record.get(catalog.CARBON_HEADLINE_KEY)),
        "wind_speed_100m": (
            record.get("wind_speed_100m", {}).get("value")
            if "wind_speed_100m" in record
            else None
        ),
        "canopy_height": (
            record.get("canopy_height", {}).get("value") if "canopy_height" in record else None
        ),
        "sea_level_rise": (
            record.get("sea_level_rise", {}).get("value") if "sea_level_rise" in record else None
        ),
        "heatwave_events": (
            record.get("heatwave_events", {}).get("value")
            if "heatwave_events" in record
            else None
        ),
        "drought_events": (
            record.get("drought_events", {}).get("value")
            if "drought_events" in record
            else None
        ),
    }


_FLAT_SCHEMA = {
    "city_id": pl.Utf8,
    "heat_warm_days_now": pl.Float64,
    "flood_100yr_share_latest": pl.Float64,
    "solar_pv_potential": pl.Float64,
    "co2_per_capita_latest": pl.Float64,
    "wind_speed_100m": pl.Float64,
    "canopy_height": pl.Float64,
    "sea_level_rise": pl.Float64,
    "heatwave_events": pl.Int64,
    "drought_events": pl.Int64,
    "climate_json": pl.Utf8,
}


def build_city_climate(ucdb: pl.DataFrame) -> pl.DataFrame:
    """Reshape ``ucdb_all`` into the per-city climate table.

    Cities with no climate attributes at all are dropped. ``city_id`` is the
    string-cast ``ID_UC_G0``; on duplicate ids one row is kept.
    """
    available = set(ucdb.columns)
    wanted = [c for c in catalog.all_attribute_columns() if c in available]
    missing = catalog.missing_columns(available)
    if missing:
        # Not fatal: absent columns become per-metric NULLs. Surface for visibility.
        print(f"  ! {len(missing)} catalog metric(s) reference columns absent from ucdb_all:")
        for key, cols in sorted(missing.items()):
            print(f"      {key}: {cols}")

    subset = ucdb.select(["ID_UC_G0", *wanted]).with_columns(
        pl.col("ID_UC_G0").cast(pl.Utf8).alias("city_id")
    )

    rows: list[dict] = []
    seen: set[str] = set()
    for row in subset.iter_rows(named=True):
        city_id = row["city_id"]
        if city_id is None or city_id in seen:
            continue
        record = build_record(row)
        if not record:  # no climate data at all -> drop
            continue
        seen.add(city_id)
        scalars = extract_headline_scalars(record)
        # event counts are integers
        for ev in ("heatwave_events", "drought_events"):
            scalars[ev] = int(scalars[ev]) if scalars[ev] is not None else None
        rows.append(
            {"city_id": city_id, **scalars, "climate_json": json.dumps(record, separators=(",", ":"))}
        )

    return pl.DataFrame(rows, schema=_FLAT_SCHEMA)


def _print_coverage(df: pl.DataFrame) -> None:
    print("\nCoverage summary:")
    print(f"  Cities with any climate data: {len(df):,}")
    for col in _FLAT_SCHEMA:
        if col in ("city_id", "climate_json"):
            continue
        n = df.select(pl.col(col).is_not_null().sum()).item()
        print(f"    {col}: {n:,} non-null")
    # per-metric coverage from the JSON records
    counts: dict[str, int] = {m.key: 0 for m in catalog.metrics()}
    for js in df["climate_json"].to_list():
        for key in json.loads(js):
            counts[key] = counts.get(key, 0) + 1
    print("  Per-metric non-null counts:")
    for metric in catalog.metrics():
        print(f"    {metric.key}: {counts.get(metric.key, 0):,}")


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
def main(force: bool = False):
    """Build city_climate.parquet from ucdb_all.parquet."""
    print("=" * 60)
    print("City Climate Build")
    print("=" * 60)

    output_path = get_processed_path("climate") / "city_climate.parquet"
    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    ucdb_path = get_interim_path("ucdb") / "ucdb_all.parquet"
    if not ucdb_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {ucdb_path}\n"
            "Run 'python -m src.cities.extract_attributes extract' first."
        )

    print(f"Loading {ucdb_path}...")
    ucdb = pl.read_parquet(ucdb_path)
    print(f"  UCDB: {len(ucdb):,} rows, {len(ucdb.columns):,} columns")

    df = build_city_climate(ucdb)

    print(f"\nSaving to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)

    _print_coverage(df)
    print(f"\nOutput: {output_path}")


if __name__ == "__main__":
    main()

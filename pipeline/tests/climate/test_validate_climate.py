"""Tests for climate validation (plan U3).

Built through the real parquet -> duckdb -> pandera path so NULL handling matches
production (pandas NaN is not an ibis NULL; polars writes true NULLs).
"""

import ibis
import pandas as pd
import pandera.ibis as pa
import polars as pl
import pytest

from src.climate.build_city_climate import _FLAT_SCHEMA
from src.validate.validate_cities import CityClimateSchema, check_foreign_keys


def _valid_rows() -> list[dict]:
    return [
        {
            "city_id": "100",
            "heat_warm_days_now": 30.0,
            "flood_100yr_share_latest": 0.12,
            "solar_pv_potential": 1500.0,
            "co2_per_capita_latest": 4.2,
            "wind_speed_100m": 6.1,
            "canopy_height": 8.0,
            "sea_level_rise": -1.2,
            "heatwave_events": 3,
            "drought_events": 1,
            "climate_json": '{"solar_pv_potential":{"value":1500.0}}',
        },
        {
            # partial-coverage city: most metrics NULL
            "city_id": "200",
            "heat_warm_days_now": None,
            "flood_100yr_share_latest": None,
            "solar_pv_potential": 1320.0,
            "co2_per_capita_latest": None,
            "wind_speed_100m": None,
            "canopy_height": None,
            "sea_level_rise": 3.4,
            "heatwave_events": None,
            "drought_events": None,
            "climate_json": '{"solar_pv_potential":{"value":1320.0}}',
        },
    ]


def _climate_table(rows: list[dict], tmp_path):
    path = tmp_path / "city_climate.parquet"
    pl.DataFrame(rows, schema=_FLAT_SCHEMA).write_parquet(path)
    con = ibis.duckdb.connect()
    return con.read_parquet(str(path))


def test_valid_climate_data_passes(tmp_path):
    table = _climate_table(_valid_rows(), tmp_path)
    CityClimateSchema.validate(table, lazy=True)  # does not raise


def test_nulls_in_partial_coverage_columns_pass(tmp_path):
    # Edge case: partial coverage — a metric present for one city, NULL for another
    # (the governance-style partial-coverage norm) validates without error.
    rows = _valid_rows()
    rows.append(
        {
            "city_id": "300",
            "heat_warm_days_now": None,
            "flood_100yr_share_latest": None,
            "solar_pv_potential": None,
            "co2_per_capita_latest": None,
            "wind_speed_100m": None,
            "canopy_height": None,
            "sea_level_rise": None,
            "heatwave_events": None,
            "drought_events": None,
            "climate_json": "{}",
        }
    )
    table = _climate_table(rows, tmp_path)
    CityClimateSchema.validate(table, lazy=True)


def test_negative_pv_potential_is_flagged(tmp_path):
    # Error path: PV potential must be >= 0
    rows = _valid_rows()
    rows[0]["solar_pv_potential"] = -5.0
    table = _climate_table(rows, tmp_path)
    with pytest.raises(pa.errors.SchemaErrors):
        CityClimateSchema.validate(table, lazy=True)


def test_flood_share_above_hundred_is_flagged(tmp_path):
    # Error path: shares are percentages bounded to [0, 100]
    rows = _valid_rows()
    rows[0]["flood_100yr_share_latest"] = 150.0
    table = _climate_table(rows, tmp_path)
    with pytest.raises(pa.errors.SchemaErrors):
        CityClimateSchema.validate(table, lazy=True)


def test_foreign_key_orphan_is_reported():
    # Error path: a climate city_id absent from cities.parquet is reported
    con = ibis.duckdb.connect()
    cities = con.create_table("cities", pd.DataFrame({"city_id": ["100", "200"]}))
    climate = con.create_table("climate", pd.DataFrame({"city_id": ["100", "999"]}))
    warnings = check_foreign_keys({"cities": cities, "climate": climate})
    assert any("climate" in w and "999" in w for w in warnings)


def test_foreign_key_all_present_no_warning():
    con = ibis.duckdb.connect()
    cities = con.create_table("cities", pd.DataFrame({"city_id": ["100", "200"]}))
    climate = con.create_table("climate", pd.DataFrame({"city_id": ["100", "200"]}))
    warnings = check_foreign_keys({"cities": cities, "climate": climate})
    assert not any("climate" in w for w in warnings)

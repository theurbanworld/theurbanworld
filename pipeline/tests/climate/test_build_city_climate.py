"""Tests for build_city_climate (plan U2)."""

import json

import polars as pl

from src.climate import build_city_climate as bcc
from src.climate import catalog


def _full_row(city_id: str, value: float = 1.0) -> dict:
    """A ucdb_all row with every catalog attribute populated."""
    row = {col: value for col in catalog.all_attribute_columns()}
    row["ID_UC_G0"] = city_id
    # categorical Köppen columns are class strings, not numbers
    koppen = catalog.by_key("koppen_class")
    for col in koppen.ucdb_attribute_ids:
        row[col] = "Cfb"
    return row


def _ucdb(rows: list[dict]) -> pl.DataFrame:
    cols = sorted(set().union(*(r.keys() for r in rows)))
    return pl.DataFrame([{c: r.get(c) for c in cols} for r in rows])


def test_full_city_yields_expected_shapes():
    df = bcc.build_city_climate(_ucdb([_full_row("100", value=2.0)]))
    assert df.height == 1
    record = json.loads(df["climate_json"][0])

    # series -> ascending points
    pec = record[catalog.CARBON_HEADLINE_KEY]
    years = [p[0] for p in pec["points"]]
    assert years == sorted(years)
    assert pec["points"][0][1] == 2.0

    # projection -> now/future
    warm = record[catalog.HEAT_HEADLINE_KEY]
    assert warm["now"] == 2.0 and warm["future"] == 2.0

    # snapshot scalar
    assert record[catalog.SOLAR_HEADLINE_KEY] == {"value": 2.0}

    # categorical projection keeps class strings
    assert record["koppen_class"] == {"now": "Cfb", "future": "Cfb"}

    # sector fingerprint -> sectors
    fp = record[catalog.CO2_SECTOR_FINGERPRINT_KEY]
    assert [s[0] for s in fp["sectors"]] == list(
        catalog.by_key(catalog.CO2_SECTOR_FINGERPRINT_KEY).sector_labels
    )


def test_headline_scalars_populated():
    df = bcc.build_city_climate(_ucdb([_full_row("100", value=3.5)]))
    r = df.row(0, named=True)
    assert r["heat_warm_days_now"] == 3.5
    assert r["solar_pv_potential"] == 3.5
    assert r["flood_100yr_share_latest"] == 3.5
    assert r["co2_per_capita_latest"] == 3.5


def test_all_null_city_is_excluded():
    null_row = {col: None for col in catalog.all_attribute_columns()}
    null_row["ID_UC_G0"] = "999"
    df = bcc.build_city_climate(_ucdb([_full_row("100"), null_row]))
    assert df["city_id"].to_list() == ["100"]


def test_inland_city_drops_marine_metric_keeps_others():
    row = _full_row("200")
    # null out marine + coastal columns (coastal-only)
    for key in ("sea_level_rise", "flood_coastal_lec"):
        for col in catalog.by_key(key).ucdb_attribute_ids:
            row[col] = None
    df = bcc.build_city_climate(_ucdb([row]))
    record = json.loads(df["climate_json"][0])
    assert "sea_level_rise" not in record
    assert "flood_coastal_lec" not in record
    # other metrics retained
    assert catalog.CARBON_HEADLINE_KEY in record
    assert catalog.SOLAR_HEADLINE_KEY in record
    assert df["sea_level_rise"][0] is None


def test_duplicate_city_id_keeps_one_row():
    df = bcc.build_city_climate(_ucdb([_full_row("300", 1.0), _full_row("300", 5.0)]))
    assert df["city_id"].to_list() == ["300"]


def test_solar_wind_are_snapshot_scalars_no_year_keys():
    # Covers R7: snapshot, no per-year points
    df = bcc.build_city_climate(_ucdb([_full_row("100")]))
    record = json.loads(df["climate_json"][0])
    assert set(record[catalog.SOLAR_HEADLINE_KEY].keys()) == {"value"}
    assert set(record["wind_speed_100m"].keys()) == {"value"}


def test_output_columns_match_flat_schema():
    # Integration: output schema matches the declared flat schema (and U3 expects it)
    df = bcc.build_city_climate(_ucdb([_full_row("100")]))
    assert df.columns == list(bcc._FLAT_SCHEMA.keys())
    assert df.schema["heatwave_events"] == pl.Int64
    assert df.schema["solar_pv_potential"] == pl.Float64


def test_partial_series_drops_null_years_only():
    row = _full_row("400")
    pec = catalog.by_key(catalog.CARBON_HEADLINE_KEY)
    # null the first two years; the rest remain
    row[pec.ucdb_attribute_ids[0]] = None
    row[pec.ucdb_attribute_ids[1]] = None
    df = bcc.build_city_climate(_ucdb([row]))
    record = json.loads(df["climate_json"][0])
    years = [p[0] for p in record[catalog.CARBON_HEADLINE_KEY]["points"]]
    assert catalog.EMISSION_YEARS[0] not in years
    assert catalog.EMISSION_YEARS[-1] in years

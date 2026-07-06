"""Tests for climate web export (plan U4)."""

import json

import polars as pl

from src.climate import catalog
from src.climate.build_city_climate import _FLAT_SCHEMA
from src.web_export import generate_climate as gc


def _row(city_id: str, **over) -> dict:
    base = {c: None for c in _FLAT_SCHEMA}
    base["city_id"] = city_id
    base["climate_json"] = "{}"
    base.update(over)
    return base


def _df(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=_FLAT_SCHEMA)


def test_summary_and_profile_shapes(tmp_path):
    record = {
        catalog.SOLAR_HEADLINE_KEY: {"value": 1500.0},
        catalog.CARBON_HEADLINE_KEY: {"points": [[1975, 1.0], [2020, 4.2]]},
    }
    df = _df(
        [
            _row(
                "100",
                heat_warm_days_now=30.0,
                flood_100yr_share_latest=0.12,
                solar_pv_potential=1500.0,
                co2_per_capita_latest=4.2,
                climate_json=json.dumps(record),
            )
        ]
    )
    manifest = gc.write_outputs(df, tmp_path)

    summary = json.loads((tmp_path / "climate_summary.json").read_text())
    profile = json.loads((tmp_path / "climate_profile.json").read_text())

    assert set(summary["100"].keys()) == set(catalog.HEADLINE_KEYS)
    assert summary["100"][catalog.SOLAR_HEADLINE_KEY] == 1500.0
    assert profile["100"][catalog.CARBON_HEADLINE_KEY]["points"][-1] == [2020, 4.2]
    assert not manifest["split"]


def test_summary_contains_only_headline_keys():
    df = _df(
        [
            _row(
                "100",
                heat_warm_days_now=30.0,
                solar_pv_potential=1500.0,
                climate_json="{}",
            )
        ]
    )
    summary = gc.build_summary(df)
    assert set(summary["100"]).issubset(set(catalog.HEADLINE_KEYS))
    # only the two non-null headline values present
    assert set(summary["100"]) == {catalog.HEAT_HEADLINE_KEY, catalog.SOLAR_HEADLINE_KEY}


def test_partial_coverage_serializes_only_present_metrics():
    # Edge case: absent metrics are omitted (keys, not nulls)
    record = {catalog.SOLAR_HEADLINE_KEY: {"value": 1320.0}}
    df = _df([_row("200", solar_pv_potential=1320.0, climate_json=json.dumps(record))])
    profile = gc.build_profile(df)
    assert list(profile["200"].keys()) == [catalog.SOLAR_HEADLINE_KEY]
    assert catalog.CARBON_HEADLINE_KEY not in profile["200"]


def test_city_with_no_headline_values_absent_from_summary():
    record = {"canopy_height": {"value": 7.0}}
    df = _df([_row("300", climate_json=json.dumps(record))])
    summary = gc.build_summary(df)
    assert "300" not in summary  # no headline values -> not in summary
    assert "300" in gc.build_profile(df)  # but present in profile


def test_oversized_profile_triggers_per_city_split(tmp_path):
    rows = []
    for i in range(5):
        rec = {catalog.CARBON_HEADLINE_KEY: {"points": [[y, float(y)] for y in range(1975, 2021, 5)]}}
        rows.append(_row(str(i), co2_per_capita_latest=2020.0, climate_json=json.dumps(rec)))
    df = _df(rows)
    manifest = gc.write_outputs(df, tmp_path, split_threshold_mb=0.0)  # force split

    assert manifest["split"]
    assert not (tmp_path / "climate_profile.json").exists()
    per_city = tmp_path / "climate" / "0.json"
    assert per_city.exists()
    assert json.loads(per_city.read_text())[catalog.CARBON_HEADLINE_KEY]["points"][0] == [1975, 1975.0]
    # summary is still a single file
    assert (tmp_path / "climate_summary.json").exists()


def test_main_local_writes_files_no_upload(tmp_path, monkeypatch):
    # Happy path: --local generates files and skips R2 upload (no creds needed)
    monkeypatch.chdir(tmp_path)
    climate_dir = tmp_path / "data" / "processed" / "climate"
    climate_dir.mkdir(parents=True)
    record = {catalog.SOLAR_HEADLINE_KEY: {"value": 1500.0}}
    _df([_row("100", solar_pv_potential=1500.0, climate_json=json.dumps(record))]).write_parquet(
        climate_dir / "city_climate.parquet"
    )

    gc.main(local_only=True)  # must not raise / must not need R2 env

    assert (tmp_path / "data" / "processed" / "tiles" / "climate_summary.json").exists()
    assert (tmp_path / "data" / "processed" / "tiles" / "climate_profile.json").exists()

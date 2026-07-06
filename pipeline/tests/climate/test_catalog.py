"""Tests for the climate metric catalog (plan U1)."""

import pytest

from src.climate import catalog
from src.climate.catalog import HEADLINE_KEYS, Lens, TemporalClass


def _fixture_columns() -> set[str]:
    """A column set representative of ucdb_all.parquet — every catalog ID present."""
    return set(catalog.all_attribute_columns()) | {"ID_UC_G0", "GC_POP_TOT_2025"}


def test_catalog_self_consistent():
    # Unique keys, valid shapes, headline flags match HEADLINE_KEYS.
    catalog.assert_catalog_consistent()


def test_every_attribute_resolves_against_fixture_columns():
    # Happy path: the catalog fully resolves; no missing columns.
    columns = _fixture_columns()
    assert catalog.missing_columns(columns) == {}
    catalog.assert_catalog_resolves(columns)  # does not raise


def test_misspelled_attribute_raises_with_offending_key_named():
    # Edge case: drop one real column -> validation names the offending metric.
    columns = _fixture_columns()
    pec = catalog.by_key(catalog.CARBON_HEADLINE_KEY)
    columns.discard(pec.ucdb_attribute_ids[0])

    missing = catalog.missing_columns(columns)
    assert catalog.CARBON_HEADLINE_KEY in missing

    with pytest.raises(ValueError) as exc:
        catalog.assert_catalog_resolves(columns)
    assert catalog.CARBON_HEADLINE_KEY in str(exc.value)


def test_series_columns_are_ascending_year_order():
    # Edge case: a series metric's per-year columns are returned ascending.
    for metric in catalog.series_metrics():
        # Trailing _YYYY suffix where present should be sorted ascending.
        years = []
        for col in metric.ucdb_attribute_ids:
            tail = col.rsplit("_", 1)[-1]
            if tail.isdigit():
                years.append(int(tail))
        assert years == sorted(years), f"{metric.key} not ascending: {years}"


def test_headline_four_present_and_flagged():
    headline = catalog.headline_metrics()
    assert tuple(m.key for m in headline) == HEADLINE_KEYS
    assert all(m.headline for m in headline)


def test_catalog_covers_every_table_a_lens():
    # Covers R1: the catalog enumerates the full Tier-0 set across all lenses.
    present = {m.lens for m in catalog.metrics()}
    assert present == set(Lens), f"missing lenses: {set(Lens) - present}"


def test_all_temporal_classes_represented():
    present = {m.temporal_class for m in catalog.metrics()}
    assert present == set(TemporalClass)


def test_sector_fingerprint_present_and_well_formed():
    fp = catalog.by_key(catalog.CO2_SECTOR_FINGERPRINT_KEY)
    assert fp.sector_fingerprint
    assert len(fp.sector_labels) == len(fp.ucdb_attribute_ids) == 4


def test_projection_metrics_have_now_future_pair_and_label():
    for metric in catalog.metrics():
        if metric.temporal_class is TemporalClass.PROJECTION:
            assert len(metric.ucdb_attribute_ids) == 2
            assert metric.future_label, f"{metric.key} missing future_label"


def test_modeled_flag_set_on_emissions_and_projections():
    # R15: emissions + projection metrics carry the modeled flag.
    assert catalog.by_key(catalog.CARBON_HEADLINE_KEY).modeled
    for metric in catalog.metrics():
        if metric.temporal_class is TemporalClass.PROJECTION:
            assert metric.modeled, f"{metric.key} projection should be modeled"

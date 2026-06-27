"""Tests for the urban-model-fit web export (U3)."""

import math

import pandas as pd

from src.web_export.generate_urban_model_fit import build_fitted_curve, generate_json


def _fits_frame(rows: list[dict]) -> pd.DataFrame:
    """Build a fits DataFrame with the parquet column names/order."""
    return pd.DataFrame(
        rows,
        columns=["city_id", "epoch", "D0", "beta", "r2", "n_rings", "reliable"],
    )


def test_nested_shape_and_keys():
    """A two-city, two-epoch fits frame produces { city: { epoch: {...} } }."""
    rows = [
        {"city_id": "A", "epoch": 2020, "D0": 12000.0, "beta": 0.18, "r2": 0.97, "n_rings": 22, "reliable": True},
        {"city_id": "A", "epoch": 2025, "D0": 11000.0, "beta": 0.17, "r2": 0.96, "n_rings": 21, "reliable": True},
        {"city_id": "B", "epoch": 2020, "D0": 8000.0, "beta": 0.09, "r2": 0.93, "n_rings": 30, "reliable": True},
        {"city_id": "B", "epoch": 2025, "D0": 8200.0, "beta": 0.09, "r2": 0.92, "n_rings": 31, "reliable": True},
    ]
    data = generate_json(_fits_frame(rows))

    assert set(data.keys()) == {"A", "B"}
    assert set(data["A"].keys()) == {"2020", "2025"}
    entry = data["A"]["2020"]
    assert set(entry.keys()) == {"D0", "beta", "r2", "reliable", "fitted"}
    assert entry["D0"] == 12000.0
    assert entry["beta"] == 0.18
    assert entry["r2"] == 0.97
    assert entry["reliable"] is True
    assert isinstance(entry["fitted"], list) and len(entry["fitted"]) > 0
    # n_rings is intentionally omitted from the JSON.
    assert "n_rings" not in entry


def test_unreliable_row_has_null_fitted_but_retains_metrics():
    """A reliable=false row serializes with fitted: null and keeps D0/beta/r2."""
    rows = [
        {"city_id": "C", "epoch": 2020, "D0": 5000.0, "beta": 0.05, "r2": 0.15, "n_rings": 12, "reliable": False},
    ]
    data = generate_json(_fits_frame(rows))
    entry = data["C"]["2020"]
    assert entry["fitted"] is None
    assert entry["D0"] == 5000.0
    assert entry["beta"] == 0.05
    assert entry["r2"] == 0.15
    assert entry["reliable"] is False


def test_unfittable_row_serializes_nulls():
    """An unfittable row (null metrics, reliable=false) serializes nulls and null fitted."""
    rows = [
        {"city_id": "D", "epoch": 2020, "D0": None, "beta": None, "r2": None, "n_rings": 1, "reliable": False},
    ]
    data = generate_json(_fits_frame(rows))
    entry = data["D"]["2020"]
    assert entry["D0"] is None
    assert entry["beta"] is None
    assert entry["r2"] is None
    assert entry["fitted"] is None


def test_fitted_curve_trims_trailing_nulls():
    """The fitted curve trims trailing near-zero values (mirrors the radial convention)."""
    # Steep beta decays to ~0 well before 50 rings, so the array is trimmed short.
    curve = build_fitted_curve(d0=10000.0, beta=0.5, num_rings=50, ring_width_km=1.0)
    assert curve[-1] is not None  # trailing nulls removed
    assert len(curve) < 50

    # First value matches the model at the first ring mid-distance (r = 0.5).
    expected_first = round(10000.0 * math.exp(-0.5 * 0.5), 1)
    assert curve[0] == expected_first

    # Curve is monotonically non-increasing where defined.
    defined = [v for v in curve if v is not None]
    assert all(a >= b for a, b in zip(defined, defined[1:]))


def test_fitted_curve_flat_profile_spans_all_rings():
    """A near-flat curve (beta=0) never rounds to zero, so it spans all rings."""
    curve = build_fitted_curve(d0=3000.0, beta=0.0, num_rings=50, ring_width_km=1.0)
    assert len(curve) == 50
    assert all(v == 3000.0 for v in curve)

"""Tests for the exponential-fit stage (U1) and reliability rule (U2).

Fit math and reliability are tested together, as the plan specifies. These tests
use synthetic radial profiles (no real parquet data is required), which is also
how the stage is verified in environments without the full pipeline dataset.
"""

import math

import polars as pl

from src.radial.compute_exponential_fits import (
    MIN_POPULATED_RINGS,
    R2_RELIABILITY_FLOOR,
    compute_fits,
    exponential_model,
    fit_exponential,
    is_reliable,
)

# Ring mid-distances for 1km rings: ring_index + 0.5
RING_DISTANCES = [i + 0.5 for i in range(50)]


def _profile_rows(city_id: str, epoch: int, densities: list[float | None]) -> list[dict]:
    """Build radial-profile parquet rows for one city-epoch from a density list."""
    rows = []
    for ring_index, density in enumerate(densities):
        rows.append(
            {
                "city_id": city_id,
                "epoch": epoch,
                "ring_index": ring_index,
                "distance_min_km": float(ring_index),
                "distance_max_km": float(ring_index + 1),
                "population": 0.0 if density is None else 1.0,
                "area_km2": 0.0 if density is None else 1.0,
                "density_per_km2": density,
                "cell_count": 0 if density is None else 1,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Fit math (U1)
# ---------------------------------------------------------------------------


def test_perfect_exponential_recovers_parameters():
    """A synthetic perfect exponential recovers D0 and beta and yields R2 approx 1.0."""
    d0_true, beta_true = 12000.0, 0.18
    distances = RING_DISTANCES[:20]
    densities = [exponential_model(r, d0_true, beta_true) for r in distances]

    d0, beta, r2, n_rings = fit_exponential(distances, densities)

    assert math.isclose(d0, d0_true, rel_tol=1e-3)
    assert math.isclose(beta, beta_true, rel_tol=1e-3)
    assert r2 is not None and r2 > 0.999
    assert n_rings == 20


def test_flat_profile_yields_near_zero_beta():
    """A constant-density profile fits without error and yields beta approx 0."""
    distances = RING_DISTANCES[:15]
    densities = [3000.0 for _ in distances]

    d0, beta, r2, n_rings = fit_exponential(distances, densities)

    assert abs(beta) < 1e-3
    assert math.isclose(d0, 3000.0, rel_tol=1e-2)
    assert n_rings == 15


def test_zero_or_one_populated_ring_does_not_raise():
    """A city-epoch with zero/one populated ring must not raise and is not fittable."""
    # zero populated rings
    d0, beta, r2, n_rings = fit_exponential([], [])
    assert n_rings == 0
    assert d0 is None and beta is None and r2 is None
    assert is_reliable(r2, n_rings) is False

    # one populated ring
    d0, beta, r2, n_rings = fit_exponential([0.5], [5000.0])
    assert n_rings == 1
    assert is_reliable(r2, n_rings) is False


def test_nulls_are_ignored_in_fit():
    """Null (empty-ring) densities are excluded from the fit; n_rings counts populated rings."""
    distances = RING_DISTANCES[:6]
    densities = [10000.0, None, 6000.0, None, 3600.0, 2160.0]
    _, _, _, n_rings = fit_exponential(distances, densities)
    assert n_rings == 4


# ---------------------------------------------------------------------------
# Reliability rule (U2)
# ---------------------------------------------------------------------------


def test_reliability_requires_minimum_populated_rings():
    """Covers AE1. Fewer than the minimum populated rings -> reliable=false."""
    n_rings = MIN_POPULATED_RINGS - 1
    assert is_reliable(0.99, n_rings) is False


def test_strong_fit_above_floor_and_ring_minimum_is_reliable():
    """A strong fit above the R2 floor and ring-count minimum -> reliable=true."""
    assert is_reliable(0.95, MIN_POPULATED_RINGS) is True


def test_low_r2_below_floor_is_unreliable_even_with_enough_rings():
    """A best fit with R2 below the floor -> reliable=false even with enough rings."""
    below = R2_RELIABILITY_FLOOR - 0.05
    assert is_reliable(below, MIN_POPULATED_RINGS + 10) is False


def test_null_r2_is_unreliable():
    """A null R2 (unfittable) is never reliable regardless of ring count."""
    assert is_reliable(None, 50) is False


# ---------------------------------------------------------------------------
# Stage output schema (U1)
# ---------------------------------------------------------------------------


def test_compute_fits_emits_one_row_per_city_epoch():
    """Output schema has exactly one row per (city_id, epoch) present in the input."""
    d0_true, beta_true = 9000.0, 0.15
    strong = [exponential_model(i + 0.5, d0_true, beta_true) for i in range(20)]
    coastal = [8000.0, 4000.0, None, None, None]  # too few populated rings

    rows = (
        _profile_rows("A", 2020, strong)
        + _profile_rows("A", 2025, strong)
        + _profile_rows("B", 2020, coastal)
    )
    profiles = pl.DataFrame(rows)

    fits = compute_fits(profiles)

    # one row per (city_id, epoch)
    assert fits.height == 3
    keys = set(
        (r["city_id"], r["epoch"]) for r in fits.select(["city_id", "epoch"]).iter_rows(named=True)
    )
    assert keys == {("A", 2020), ("A", 2025), ("B", 2020)}

    # expected columns present
    assert set(fits.columns) == {
        "city_id",
        "epoch",
        "D0",
        "beta",
        "r2",
        "n_rings",
        "reliable",
    }

    # strong city-epoch is reliable; coastal one is not
    a2020 = fits.filter((pl.col("city_id") == "A") & (pl.col("epoch") == 2020)).to_dicts()[0]
    b2020 = fits.filter((pl.col("city_id") == "B") & (pl.col("epoch") == 2020)).to_dicts()[0]
    assert a2020["reliable"] is True
    assert math.isclose(a2020["beta"], beta_true, rel_tol=1e-2)
    assert b2020["reliable"] is False


def test_compute_fits_handles_empty_input():
    """An empty profiles frame returns an empty, correctly-typed fits frame."""
    empty = pl.DataFrame(
        schema={
            "city_id": pl.Utf8,
            "epoch": pl.Int64,
            "ring_index": pl.Int64,
            "distance_min_km": pl.Float64,
            "distance_max_km": pl.Float64,
            "population": pl.Float64,
            "area_km2": pl.Float64,
            "density_per_km2": pl.Float64,
            "cell_count": pl.Int64,
        }
    )
    fits = compute_fits(empty)
    assert fits.height == 0
    assert fits.schema["reliable"] == pl.Boolean


# ---------------------------------------------------------------------------
# Output schema validation (U2)
# ---------------------------------------------------------------------------


def _validate_fits(frame: pl.DataFrame, tmp_path):
    """Validate a fits frame against ExponentialFitSchema via the ibis backend."""
    import ibis
    import pandera.ibis as pa

    from src.validate.validate_cities import ExponentialFitSchema

    path = tmp_path / "radial_fits_h3_r8.parquet"
    frame.write_parquet(path)
    con = ibis.duckdb.connect()
    table = con.read_parquet(str(path))
    ExponentialFitSchema.validate(table, lazy=True)
    return pa  # for callers that want the errors type


def test_valid_fits_parquet_passes_schema(tmp_path):
    """A well-formed fits parquet (reliable + honest-null rows) passes the schema."""
    frame = pl.DataFrame(
        {
            "city_id": ["A", "B"],
            "epoch": [2020, 2020],
            "D0": [12000.0, None],
            "beta": [0.18, None],
            "r2": [0.97, None],
            "n_rings": [22, 2],
            "reliable": [True, False],
        },
        schema={
            "city_id": pl.Utf8,
            "epoch": pl.Int64,
            "D0": pl.Float64,
            "beta": pl.Float64,
            "r2": pl.Float64,
            "n_rings": pl.Int64,
            "reliable": pl.Boolean,
        },
    )
    # Should not raise.
    _validate_fits(frame, tmp_path)


def test_schema_rejects_r2_above_one(tmp_path):
    """A row with r2 > 1.0 fails schema validation."""
    import pandera.ibis as pa

    frame = pl.DataFrame(
        {
            "city_id": ["A"],
            "epoch": [2020],
            "D0": [12000.0],
            "beta": [0.18],
            "r2": [1.5],
            "n_rings": [22],
            "reliable": [True],
        }
    )
    try:
        _validate_fits(frame, tmp_path)
        raise AssertionError("expected SchemaErrors for r2 > 1.0")
    except pa.errors.SchemaErrors:
        pass


def test_reliability_consistency_flags_null_beta_on_reliable_row(tmp_path):
    """A reliable row with null beta is flagged by the consistency check."""
    import ibis

    from src.validate.validate_cities import check_fit_reliability_consistency

    frame = pl.DataFrame(
        {
            "city_id": ["A"],
            "epoch": [2020],
            "D0": [12000.0],
            "beta": [None],
            "r2": [0.9],
            "n_rings": [22],
            "reliable": [True],
        },
        schema={
            "city_id": pl.Utf8,
            "epoch": pl.Int64,
            "D0": pl.Float64,
            "beta": pl.Float64,
            "r2": pl.Float64,
            "n_rings": pl.Int64,
            "reliable": pl.Boolean,
        },
    )
    path = tmp_path / "radial_fits_h3_r8.parquet"
    frame.write_parquet(path)
    con = ibis.duckdb.connect()
    warnings = check_fit_reliability_consistency({"fits": con.read_parquet(str(path))})
    assert warnings and "reliable rows with null" in warnings[0]

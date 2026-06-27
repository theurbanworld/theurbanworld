"""
Fit the Standard Urban Model (monocentric exponential) to radial density profiles.

Purpose: For each (city_id, epoch), fit D(r) = D0 * e^(-beta * r) to the observed
         radial density profile and emit the fitted parameters, goodness-of-fit, and
         a reliability flag. This is the Alonso-Muth-Mills monocentric baseline that
         the web app overlays on the observed profile and translates into two
         plain-language axes (compactness from beta, structure from R^2).

Input:
  - data/processed/radial_profiles/radial_profiles_h3_r8.parquet

Output:
  - data/processed/radial_profiles/radial_fits_h3_r8.parquet

Output Schema (radial_fits_h3_r8.parquet):
  | Column   | Type    | Description                                         |
  |----------|---------|-----------------------------------------------------|
  | city_id  | String  | Primary key from UCDB                               |
  | epoch    | Int64   | Year (1975, 1980, ..., 2030)                        |
  | D0       | Float64 | Fitted central density (people/km^2), null if unfit |
  | beta     | Float64 | Fitted density gradient (1/km), null if unfit       |
  | r2       | Float64 | R^2 of the fit on the original scale, null if unfit |
  | n_rings  | Int64   | Number of populated rings used in the fit           |
  | reliable | Boolean | Whether the fit meets the reliability criteria      |

Decision log:
  - Model fit with scipy.optimize.curve_fit (nonlinear least squares on the original
    density scale), seeded by a log-linear initial guess for robust convergence
    (KTD1). Falls back to the log-linear estimate if curve_fit does not converge.
  - R^2 computed on the original (non-log) scale, against the mean.
  - reliable=false rows are kept (not dropped) so the web can render honest-null
    rather than mislabel coastal/clipped/tiny cities (KTD4).
  - Reliability thresholds are literature-anchored placeholders (KTD5); they should be
    recalibrated against the real fit distribution once it is available, and the chosen
    values recorded in the methodology content (U11).
Date: 2026-06-27
"""


import click
import numpy as np
import polars as pl
from scipy.optimize import curve_fit

from ..utils.config import config, get_processed_path

# =============================================================================
# Reliability criteria (U2)
#
# KTD5 placeholders, literature-anchored. These suppress the badge / fitted curve
# for fits that are not trustworthy (coastal, clipped, or tiny cities) WITHOUT
# suppressing legitimately polycentric cities -- a city with a real but poor
# monocentric fit (low-ish R^2) is still "reliable" and is honestly labelled
# "Multi-centered / Irregular" in the web. The reliability floor is therefore well
# below the web's structure cutoff (R^2 ~= 0.9, see web/app/utils/urbanModelLabels.ts).
#
# Recalibrate against the real fit distribution when available; the count of
# reliable=true city-epochs should be a plausible majority, not near-zero/near-total.
# =============================================================================

# Minimum number of populated rings for an exponential fit to be meaningful.
# Fewer rings means a coastal/clipped or very small city where the monocentric
# baseline cannot be trusted.
MIN_POPULATED_RINGS = 5

# R^2 floor below which the exponential model explains too little variance to be
# trustworthy at all. Distinct from (and far below) the web's monocentric cutoff.
R2_RELIABILITY_FLOOR = 0.2


RADIAL_PROFILES_FILENAME = "radial_profiles_h3_r8.parquet"
RADIAL_FITS_FILENAME = "radial_fits_h3_r8.parquet"

_FITS_SCHEMA = {
    "city_id": pl.Utf8,
    "epoch": pl.Int64,
    "D0": pl.Float64,
    "beta": pl.Float64,
    "r2": pl.Float64,
    "n_rings": pl.Int64,
    "reliable": pl.Boolean,
}


def exponential_model(r: np.ndarray | float, d0: float, beta: float) -> np.ndarray | float:
    """Monocentric Standard Urban Model: D(r) = D0 * e^(-beta * r)."""
    return d0 * np.exp(-beta * r)


def fit_exponential(
    distances: list[float], densities: list[float | None]
) -> tuple[float | None, float | None, float | None, int]:
    """Fit D(r) = D0 * e^(-beta * r) to one city-epoch radial profile.

    Args:
        distances: Ring mid-distances in km (same length as densities).
        densities: Observed density per ring; None/0 for empty rings (ignored).

    Returns:
        (D0, beta, r2, n_rings). The first three are None when fewer than two
        populated rings make the fit undefined. n_rings is the count of populated
        rings used.
    """
    d = np.asarray(densities, dtype=float)
    r = np.asarray(distances, dtype=float)

    # Fit the positive-density envelope. We deliberately drop both null rings
    # (no H3 cells) and exact-zero rings (cells but no population — water, parks,
    # airfields): the exponential model is strictly positive, so a zero observation
    # is something it structurally cannot represent, and the log-linear seed needs
    # d > 0. n_rings therefore counts populated rings, which also feeds the
    # reliability gate — undercounting coastal/clipped cities toward "unreliable"
    # is the intended honest-null behaviour.
    mask = np.isfinite(d) & (d > 0)
    r = r[mask]
    d = d[mask]
    n_rings = int(r.size)

    if n_rings < 2:
        return None, None, None, n_rings

    # Log-linear initial guess: ln(D) = ln(D0) - beta * r.
    try:
        slope, intercept = np.polyfit(r, np.log(d), 1)
        d0_guess = float(np.exp(intercept))
        beta_guess = float(-slope)
    except (np.linalg.LinAlgError, ValueError):
        d0_guess, beta_guess = float(d.max()), 0.1

    if not np.isfinite(d0_guess) or d0_guess <= 0:
        d0_guess = float(d.max())
    if not np.isfinite(beta_guess):
        beta_guess = 0.1

    # Nonlinear least squares on the original scale, seeded by the log-linear guess.
    try:
        popt, _ = curve_fit(
            exponential_model,
            r,
            d,
            p0=[d0_guess, beta_guess],
            maxfev=10000,
        )
        d0, beta = float(popt[0]), float(popt[1])
    except (RuntimeError, ValueError):
        # curve_fit did not converge -> use the log-linear estimate.
        d0, beta = d0_guess, beta_guess

    # The model is a strictly-positive central density; an unbounded optimum can
    # land on D0 <= 0 (or non-finite) for noisy/non-monocentric profiles, which would
    # both fail the D0 > 0 output schema and draw a curve below zero. Fall back to the
    # log-linear estimate (D0 = exp(intercept) > 0 by construction) in that case.
    if not np.isfinite(d0) or d0 <= 0 or not np.isfinite(beta):
        d0, beta = d0_guess, beta_guess

    # R^2 on the original scale, against the mean.
    pred = np.asarray(exponential_model(r, d0, beta), dtype=float)
    ss_res = float(np.sum((d - pred) ** 2))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    if ss_tot > 0:
        r2: float | None = 1.0 - ss_res / ss_tot
    else:
        # Flat profile (all populated densities equal): a constant model fits perfectly.
        # Use a relative tolerance — an absolute floor is unreachable for densities in
        # the thousands.
        r2 = 1.0 if np.allclose(pred, d, rtol=1e-3, atol=1e-6) else None

    if r2 is not None and not np.isfinite(r2):
        r2 = None
    if r2 is not None:
        r2 = min(r2, 1.0)  # clip the upper bound; negative R^2 is meaningful (worse than mean)

    return d0, beta, r2, n_rings


def is_reliable(r2: float | None, n_rings: int) -> bool:
    """Reliability rule (U2): enough populated rings AND a fit above the R^2 floor."""
    if r2 is None:
        return False
    return n_rings >= MIN_POPULATED_RINGS and r2 >= R2_RELIABILITY_FLOOR


def compute_fits(profiles: pl.DataFrame) -> pl.DataFrame:
    """Compute one fit row per (city_id, epoch) from a radial-profiles frame."""
    if profiles.height == 0:
        return pl.DataFrame(schema=_FITS_SCHEMA)

    rows: list[dict] = []
    # One partition per city-epoch.
    for part in profiles.partition_by(["city_id", "epoch"], maintain_order=True):
        part = part.sort("ring_index")
        city_id = part["city_id"][0]
        epoch = int(part["epoch"][0])

        mid_distances = (
            (part["distance_min_km"] + part["distance_max_km"]) / 2.0
        ).to_list()
        densities = part["density_per_km2"].to_list()

        d0, beta, r2, n_rings = fit_exponential(mid_distances, densities)
        rows.append(
            {
                "city_id": str(city_id),
                "epoch": epoch,
                "D0": d0,
                "beta": beta,
                "r2": r2,
                "n_rings": n_rings,
                "reliable": is_reliable(r2, n_rings),
            }
        )

    return pl.DataFrame(rows, schema=_FITS_SCHEMA)


def compute_all_fits() -> pl.DataFrame:
    """Load the radial-profiles parquet and compute fits for every city-epoch."""
    profiles_path = get_processed_path("radial_profiles") / RADIAL_PROFILES_FILENAME
    if not profiles_path.exists():
        raise FileNotFoundError(f"Missing radial profiles: {profiles_path}")

    print(f"Loading radial profiles from {profiles_path}...")
    profiles = pl.read_parquet(profiles_path)
    print(
        f"  Loaded {profiles.height:,} rows "
        f"({profiles['city_id'].n_unique():,} cities, "
        f"{profiles['epoch'].n_unique()} epochs)"
    )

    print("Fitting exponential model per city-epoch...")
    fits = compute_fits(profiles)
    return fits


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing output")
def main(force: bool = False):
    """Fit the monocentric exponential model to radial density profiles."""
    print("=" * 60)
    print("Exponential Fit Computation (Standard Urban Model)")
    print("=" * 60)

    output_dir = get_processed_path("radial_profiles")
    output_path = output_dir / RADIAL_FITS_FILENAME

    if output_path.exists() and not force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite")
        return

    print(f"\n  Min populated rings for reliability: {MIN_POPULATED_RINGS}")
    print(f"  R^2 reliability floor: {R2_RELIABILITY_FLOOR}")
    print(f"  Epochs: {config.GHSL_POP_EPOCHS}\n")

    fits = compute_all_fits()

    print(f"\nSaving to {output_path}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    fits.write_parquet(output_path)

    # Summary
    n_reliable = int(fits["reliable"].sum())
    print("\n" + "=" * 60)
    print("Fit Computation Complete")
    print("=" * 60)
    print(f"Total city-epochs: {fits.height:,}")
    print(f"Reliable fits: {n_reliable:,} ({100 * n_reliable / max(fits.height, 1):.1f}%)")
    reliable = fits.filter(pl.col("reliable"))
    if reliable.height > 0:
        print(
            "Reliable beta range: "
            f"[{reliable['beta'].min():.3f}, {reliable['beta'].max():.3f}], "
            f"median {reliable['beta'].median():.3f}"
        )
        print(
            "Reliable R^2 range: "
            f"[{reliable['r2'].min():.3f}, {reliable['r2'].max():.3f}], "
            f"median {reliable['r2'].median():.3f}"
        )
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()

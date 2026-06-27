"""Declarative climate metric catalog — the single source of truth.

Each metric maps a stable ``key`` to the resolved UCDB column name(s) it reads,
its lens, its temporal class, unit, upstream source, methodology path, and
honesty flags. The pipeline (``build_city_climate.py``) reads this to select and
reshape columns; the web mirror (``web/types/climate.ts``) reads an aligned
descriptor to drive rendering, rankings, and methodology links.

This keeps UCDB attribute IDs from scattering across pipeline and web code, and
makes "add/remove a metric" a single catalog edit.

IMPORTANT — column-name pinning (plan U1, deferred-to-implementation):
  Materialized UCDB column names carry year suffixes, casing, and BOM/trailing
  -space artifacts that the documented ``XX_XXX_XXX_YYYY`` IDs only approximate.
  The ``ucdb_attribute_ids`` below follow the documented JRC R2024A schema. Before
  the build runs against real data, regenerate the schema and resolve names:

      uv run python -m src.cities.extract_attributes schema   # -> ucdb_schema.json
      # then confirm against an actual column listing of ucdb_all.parquet

  ``assert_catalog_resolves()`` fails loudly on any drift, so a name that the real
  parquet does not contain is caught before downstream units depend on it. The
  catalog is the one place that absorbs divergence from the documented IDs.

Mirror invariant: keep metric keys, temporal classes, and methodology paths in
sync with ``web/types/climate.ts``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# Temporal classes & lenses
# ---------------------------------------------------------------------------


class TemporalClass(str, Enum):
    """How a metric renders. The section dispatches on this tag."""

    SERIES = "series"  # multi-year values on the metric's own native x-axis
    PROJECTION = "projection"  # a now value and a modeled future value
    SNAPSHOT = "snapshot"  # a single value, no implied trend


class Lens(str, Enum):
    """The thematic grouping a metric belongs to on the city page."""

    HEAT = "heat"
    FLOOD = "flood"
    CLIMATE_TYPE = "climate_type"
    GREENNESS = "greenness"
    ENERGY = "energy"
    FOOTPRINT = "footprint"
    URBAN_FORM = "urban_form"
    HAZARD = "hazard"


# ---------------------------------------------------------------------------
# Year spines (documented temporal coverage per origin Table A)
# ---------------------------------------------------------------------------

# Pinned against ucdb_all.parquet (R2024A). EDGAR per-capita CO2 spine.
EMISSION_YEARS = (1975, 1990, 2000, 2005, 2010, 2015, 2020)
# EDGAR totals/sectors extend one epoch further, to 2022.
EMISSION_TOTAL_YEARS = (1975, 1990, 2000, 2005, 2010, 2015, 2020, 2022)
# Exposure shares ride the population epoch spine 1975-2030 (all 12 epochs present).
EXPOSURE_YEARS = (1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030)
# Greenness / green-space access 1985-2025.
GREENNESS_YEARS = (1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025)
# UTCI heat-stress decadal 1970-2020.
UTCI_YEARS = (1970, 1980, 1990, 2000, 2010, 2020)
# SDG 11.3.1 land-use efficiency is stored as period-range columns (start_end);
# the END year of each period is the series point year.
LUE_PERIOD_COLUMNS = (
    "SD_LUE_LPR_1975_1980",
    "SD_LUE_LPR_1980_1990",
    "SD_LUE_LPR_1990_2000",
    "SD_LUE_LPR_2000_2010",
    "SD_LUE_LPR_2010_2020",
    "SD_LUE_LPR_2020_2030",
)
# Wildfire burnt area is a sparse 3-epoch record.
WILDFIRE_COLUMNS = ("HZ_WLF_BHA_2015", "HZ_WLF_BHA_2020", "HZ_WLF_BHA_2024")


def _year_cols(base: str, years: Iterable[int]) -> tuple[str, ...]:
    """Expand a base attribute ID into ordered per-year column names.

    Documented UCDB year-suffixed columns follow ``PREFIX_YYYY`` (e.g.
    ``GC_POP_TOT_2025``). Ascending-year order is guaranteed for ``series``
    rendering.
    """
    return tuple(f"{base}_{year}" for year in sorted(years))


# ---------------------------------------------------------------------------
# Methodology content paths (resolved by useInfoModal -> @nuxt/content)
# ---------------------------------------------------------------------------

_M_OVERVIEW = "/methodology/climate-energy"
_M_EDGAR = "/data/source-edgar"
_M_SOLAR = "/data/source-solar-atlas"
_M_WIND = "/data/source-wind-atlas"
_M_KOPPEN = "/data/source-koppen"
_M_LCZ = "/data/source-lcz"
_M_C3S = "/data/source-c3s"
_M_EXPOSURE = "/data/source-exposure"
_M_GREENNESS = "/data/source-greenness"
_M_SDG = "/data/source-sdg"
_M_HAZARD = "/data/source-hazard"


# ---------------------------------------------------------------------------
# Metric descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Metric:
    """One climate/energy metric.

    Fields mirror ``web/types/climate.ts`` ``ClimateMetricDescriptor`` (the web
    side omits ``ucdb_attribute_ids`` and ``categorical``, which only the
    pipeline needs).
    """

    key: str
    label: str
    lens: Lens
    temporal_class: TemporalClass
    # Resolved real column names. SERIES -> ordered per-year columns;
    # PROJECTION -> (now_col, future_col); SNAPSHOT -> one or more columns.
    ucdb_attribute_ids: tuple[str, ...]
    unit: str | None
    source: str
    methodology_path: str
    modeled: bool
    headline: bool = False
    # Future-value label for PROJECTION metrics (e.g. "2070, SSP5-8.5").
    future_label: str | None = None
    # Categorical (non-numeric) value, e.g. Köppen class codes.
    categorical: bool = False
    # The CO2 sector-fingerprint companion to the per-capita CO2 headline.
    # Its ucdb_attribute_ids are the per-sector columns (energy/transport/
    # industry/residential); the build emits per-sector shares.
    sector_fingerprint: bool = False
    # Sector labels, parallel to ucdb_attribute_ids, for sector_fingerprint.
    sector_labels: tuple[str, ...] = field(default_factory=tuple)


# Stable keys referenced elsewhere (headline rankings, fingerprint coupling).
HEAT_HEADLINE_KEY = "heat_warm_days"
FLOOD_HEADLINE_KEY = "flood_100yr_share"
SOLAR_HEADLINE_KEY = "solar_pv_potential"
CARBON_HEADLINE_KEY = "co2_per_capita"
CO2_SECTOR_FINGERPRINT_KEY = "co2_sector_fingerprint"

HEADLINE_KEYS = (
    HEAT_HEADLINE_KEY,
    FLOOD_HEADLINE_KEY,
    SOLAR_HEADLINE_KEY,
    CARBON_HEADLINE_KEY,
)


# ---------------------------------------------------------------------------
# The catalog — ordered; headline four lead within their lens
# ---------------------------------------------------------------------------

CATALOG: tuple[Metric, ...] = (
    # --- Heat (Climate risk) --------------------------------------------
    Metric(
        key=HEAT_HEADLINE_KEY,
        label="Warm days (TX90p)",
        lens=Lens.HEAT,
        temporal_class=TemporalClass.PROJECTION,
        ucdb_attribute_ids=("CL_WDS_CUR_2010", "CL_WDS_585_2030"),
        unit="days/year",
        source="C3S / CMIP6 (TX90p index)",
        methodology_path=_M_C3S,
        modeled=True,
        headline=True,
        future_label="2030, SSP5-8.5",
    ),
    Metric(
        key="heat_utci_t32",
        label="Days UTCI > 32 °C",
        lens=Lens.HEAT,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("CL_UTC_T32", UTCI_YEARS),
        unit="days/year",
        source="C3S thermal-comfort (UTCI)",
        methodology_path=_M_C3S,
        modeled=True,
    ),
    Metric(
        key="heat_mean_temp",
        label="Annual mean temperature",
        lens=Lens.HEAT,
        temporal_class=TemporalClass.PROJECTION,
        ucdb_attribute_ids=("CL_B01_CUR_2010", "CL_B01_P85_2030"),
        unit="°C",
        source="C3S / CMIP6 (bioclimatic BIO1)",
        methodology_path=_M_C3S,
        modeled=True,
        future_label="2030, RCP8.5",
    ),
    # --- Flood & water (Climate risk) -----------------------------------
    Metric(
        key=FLOOD_HEADLINE_KEY,
        label="Population in 100-yr flood zone",
        lens=Lens.FLOOD,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("EX_100_SHP", EXPOSURE_YEARS),
        unit="share",
        source="GHS-UCDB exposure (100-yr return-period flood model)",
        methodology_path=_M_EXPOSURE,
        modeled=True,
        headline=True,
    ),
    Metric(
        key="flood_coastal_lec",
        label="Population ≤10 m coastal elevation",
        lens=Lens.FLOOD,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("EX_LEC_SHP", EXPOSURE_YEARS),
        unit="share",
        source="GHS-UCDB exposure (low-elevation coastal zone)",
        methodology_path=_M_EXPOSURE,
        modeled=True,
    ),
    Metric(
        key="sea_level_rise",
        label="Local sea-level-rise rate",
        lens=Lens.FLOOD,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=("WA_MAR_SHT_2023",),
        unit="mm/year",
        source="GHS-UCDB water (marine trend)",
        methodology_path=_M_EXPOSURE,
        modeled=True,
    ),
    # --- Climate type & morphology --------------------------------------
    Metric(
        key="koppen_class",
        label="Köppen climate type",
        lens=Lens.CLIMATE_TYPE,
        temporal_class=TemporalClass.PROJECTION,
        ucdb_attribute_ids=("CL_KOP_CUR_2025", "CL_KOP_585_2070"),
        unit=None,
        source="Köppen-Geiger (Beck et al. 2018)",
        methodology_path=_M_KOPPEN,
        modeled=True,
        future_label="2070, SSP5-8.5",
        categorical=True,
    ),
    Metric(
        key="lcz_composition",
        label="Local Climate Zone composition",
        lens=Lens.CLIMATE_TYPE,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=tuple(f"CL_LCZ_A{n:02d}_2025" for n in range(1, 18)),
        unit="share",
        source="Local Climate Zones (Demuzere et al. 2022)",
        methodology_path=_M_LCZ,
        modeled=False,
    ),
    # --- Energy resource -------------------------------------------------
    Metric(
        key=SOLAR_HEADLINE_KEY,
        label="Solar PV potential",
        lens=Lens.ENERGY,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=("CL_REN_PVO_2020",),
        unit="kWh/kWp",
        source="Global Solar Atlas 2.0 (ESMAP 2020)",
        methodology_path=_M_SOLAR,
        modeled=False,
        headline=True,
    ),
    Metric(
        key="wind_speed_100m",
        label="Wind speed @100 m",
        lens=Lens.ENERGY,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=("CL_REN_W10_2020",),
        unit="m/s",
        source="Global Wind Atlas (Davis et al. 2023)",
        methodology_path=_M_WIND,
        modeled=False,
    ),
    # --- Footprint (Emissions) ------------------------------------------
    Metric(
        key=CARBON_HEADLINE_KEY,
        label="Per-capita CO₂",
        lens=Lens.FOOTPRINT,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("EM_CO2_PEC", EMISSION_YEARS),
        unit="t CO₂/person",
        source="EDGAR v8.0 (Crippa et al. 2024)",
        methodology_path=_M_EDGAR,
        modeled=True,
        headline=True,
    ),
    Metric(
        key=CO2_SECTOR_FINGERPRINT_KEY,
        label="CO₂ sector fingerprint",
        lens=Lens.FOOTPRINT,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=(
            "EM_CO2_SEN_2022",
            "EM_CO2_STR_2022",
            "EM_CO2_SIN_2022",
            "EM_CO2_SRE_2022",
        ),
        unit="share",
        source="EDGAR v8.0 (Crippa et al. 2024)",
        methodology_path=_M_EDGAR,
        modeled=True,
        sector_fingerprint=True,
        sector_labels=("Energy", "Transport", "Industry", "Residential"),
    ),
    Metric(
        key="co2_total",
        label="Total CO₂ emissions",
        lens=Lens.FOOTPRINT,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("EM_CO2_TOT", EMISSION_TOTAL_YEARS),
        unit="t CO₂/year",
        source="EDGAR v8.0 (Crippa et al. 2024)",
        methodology_path=_M_EDGAR,
        modeled=True,
    ),
    Metric(
        key="ghg_total",
        label="Total GHG emissions",
        lens=Lens.FOOTPRINT,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("EM_GHG_TOT", EMISSION_TOTAL_YEARS),
        unit="t CO₂-eq/year",
        source="EDGAR v8.0 (Crippa et al. 2024)",
        methodology_path=_M_EDGAR,
        modeled=True,
    ),
    Metric(
        key="pm25_emissions",
        label="PM₂.₅ emissions",
        lens=Lens.FOOTPRINT,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("EM_PM2_TOT", EMISSION_TOTAL_YEARS),
        unit="t/year",
        source="EDGAR v8.0 (Crippa et al. 2024)",
        methodology_path=_M_EDGAR,
        modeled=True,
    ),
    # --- Urban form ------------------------------------------------------
    Metric(
        key="land_use_efficiency",
        label="Land-use efficiency (SDG 11.3.1)",
        lens=Lens.URBAN_FORM,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=LUE_PERIOD_COLUMNS,
        unit="ratio",
        source="UN-Habitat SDG 11.3.1 (land-consumption / population rate)",
        methodology_path=_M_SDG,
        modeled=False,
    ),
    # --- Greenness & livability -----------------------------------------
    Metric(
        key="greenness_built",
        label="High-greenness built-up share",
        lens=Lens.GREENNESS,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("GR_SHB_HGR", GREENNESS_YEARS),
        unit="share",
        source="GHS-UCDB greenness (Landsat NDVI)",
        methodology_path=_M_GREENNESS,
        modeled=False,
    ),
    Metric(
        key="greenness_mean",
        label="Mean greenness in built-up",
        lens=Lens.GREENNESS,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("GR_AVG_GRN", GREENNESS_YEARS),
        unit="index",
        source="GHS-UCDB greenness (Landsat NDVI)",
        methodology_path=_M_GREENNESS,
        modeled=False,
    ),
    Metric(
        key="green_space_access",
        label="Population with green-space access",
        lens=Lens.GREENNESS,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=_year_cols("SD_POP_HGR", GREENNESS_YEARS),
        unit="share",
        source="GHS-UCDB SDG 11.7 (green-space access)",
        methodology_path=_M_GREENNESS,
        modeled=False,
    ),
    Metric(
        key="canopy_height",
        label="Mean tree-canopy height",
        lens=Lens.GREENNESS,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=("GR_CTH_AVG_2020",),
        unit="m",
        source="GHS-UCDB canopy height (Lang et al.)",
        methodology_path=_M_GREENNESS,
        modeled=False,
    ),
    # --- Hazard occurrence ----------------------------------------------
    Metric(
        key="wildfire_burnt_area",
        label="Wildfire burnt area",
        lens=Lens.HAZARD,
        temporal_class=TemporalClass.SERIES,
        ucdb_attribute_ids=WILDFIRE_COLUMNS,
        unit="ha/year",
        source="GHS-UCDB hazard (burnt-area record)",
        methodology_path=_M_HAZARD,
        modeled=False,
    ),
    Metric(
        key="heatwave_events",
        label="Heatwave events",
        lens=Lens.HAZARD,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=("HZ_CEV_HEW_2015",),
        unit="count",
        source="GHS-UCDB hazard (climate-event counts)",
        methodology_path=_M_HAZARD,
        modeled=True,
    ),
    Metric(
        key="drought_events",
        label="Drought events",
        lens=Lens.HAZARD,
        temporal_class=TemporalClass.SNAPSHOT,
        ucdb_attribute_ids=("HZ_CEV_DRO_2015",),
        unit="count",
        source="GHS-UCDB hazard (climate-event counts)",
        methodology_path=_M_HAZARD,
        modeled=True,
    ),
)


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def metrics() -> tuple[Metric, ...]:
    """All metrics in catalog order."""
    return CATALOG


def by_key(key: str) -> Metric:
    """Look up a metric by key, raising ``KeyError`` if unknown."""
    for metric in CATALOG:
        if metric.key == key:
            return metric
    raise KeyError(f"Unknown climate metric key: {key!r}")


def headline_metrics() -> tuple[Metric, ...]:
    """The four headline metrics, in HEADLINE_KEYS order."""
    return tuple(by_key(k) for k in HEADLINE_KEYS)


def series_metrics() -> tuple[Metric, ...]:
    return tuple(m for m in CATALOG if m.temporal_class is TemporalClass.SERIES)


def all_attribute_columns() -> set[str]:
    """Every real UCDB column referenced anywhere in the catalog."""
    cols: set[str] = set()
    for metric in CATALOG:
        cols.update(metric.ucdb_attribute_ids)
    return cols


# ---------------------------------------------------------------------------
# Validation — fail loudly on column-name drift
# ---------------------------------------------------------------------------


def missing_columns(columns: Iterable[str]) -> dict[str, list[str]]:
    """Return ``{metric_key: [missing column, ...]}`` for unresolved attributes.

    ``columns`` is the set of actual column names available (e.g. from
    ``ucdb_all.parquet``). An empty dict means the catalog fully resolves.
    """
    available = set(columns)
    out: dict[str, list[str]] = {}
    for metric in CATALOG:
        missing = [c for c in metric.ucdb_attribute_ids if c not in available]
        if missing:
            out[metric.key] = missing
    return out


def assert_catalog_resolves(columns: Iterable[str]) -> None:
    """Raise ``ValueError`` naming the offending keys if any attribute is absent.

    This is the drift guard the plan calls for: run it against the real
    ``ucdb_all.parquet`` columns so a documented ID that does not match the
    materialized name fails before downstream units depend on it.
    """
    missing = missing_columns(columns)
    if missing:
        details = "; ".join(f"{key}: {cols}" for key, cols in sorted(missing.items()))
        raise ValueError(
            "Climate catalog does not resolve against the provided columns — "
            f"unresolved attribute IDs by metric: {details}"
        )


def assert_catalog_consistent() -> None:
    """Internal self-checks independent of any data: keys unique, shapes valid."""
    keys = [m.key for m in CATALOG]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"Duplicate metric keys in catalog: {sorted(dupes)}")

    for metric in CATALOG:
        if not metric.ucdb_attribute_ids:
            raise ValueError(f"{metric.key}: no ucdb_attribute_ids")
        if metric.temporal_class is TemporalClass.PROJECTION:
            if len(metric.ucdb_attribute_ids) != 2:
                raise ValueError(
                    f"{metric.key}: projection metrics need exactly (now, future) columns"
                )
        if metric.sector_fingerprint and len(metric.sector_labels) != len(
            metric.ucdb_attribute_ids
        ):
            raise ValueError(
                f"{metric.key}: sector_labels must be parallel to ucdb_attribute_ids"
            )

    headline = {m.key for m in CATALOG if m.headline}
    if headline != set(HEADLINE_KEYS):
        raise ValueError(
            f"Headline flag set {sorted(headline)} != HEADLINE_KEYS {sorted(HEADLINE_KEYS)}"
        )

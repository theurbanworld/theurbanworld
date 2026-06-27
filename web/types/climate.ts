/**
 * Climate & Energy metric descriptors — the web mirror of the pipeline catalog.
 *
 * This file mirrors `pipeline/src/climate/catalog.py`. The two MUST stay aligned:
 * metric keys, temporal classes, and methodology paths. Drift surfaces as missing
 * rendering or unresolved methodology links. The pipeline omits per-city `ucdb_attribute_ids`
 * from the JSON it ships; the web only needs the presentation descriptor below.
 *
 * The per-city values arrive from `climate_profile.json` as a `ClimateRecord`
 * (metric key -> value shape) and `climate_summary.json` as headline scalars.
 */

export type TemporalClass = 'series' | 'projection' | 'snapshot'

export type ClimateLens
  = | 'heat'
    | 'flood'
    | 'climate_type'
    | 'greenness'
    | 'energy'
    | 'footprint'
    | 'urban_form'
    | 'hazard'

/** Presentation descriptor for one metric (mirrors catalog.Metric, UI fields only). */
export interface ClimateMetricDescriptor {
  key: string
  label: string
  lens: ClimateLens
  temporalClass: TemporalClass
  unit: string | null
  source: string
  methodologyPath: string
  modeled: boolean
  headline: boolean
  /** Future-value label for projection metrics (e.g. "2070, SSP5-8.5"). */
  futureLabel?: string
  /** Categorical (non-numeric) value, e.g. Köppen class codes. */
  categorical?: boolean
  /** The CO₂ sector-fingerprint companion to the per-capita CO₂ headline. */
  sectorFingerprint?: boolean
}

// --- Per-city value shapes (as serialized by build_city_climate.py) ----------

/** series -> ascending [year, value] points. */
export interface SeriesValue {
  points: [number, number][]
}
/** projection -> a now value and a modeled future value (categorical allowed). */
export interface ProjectionValue {
  now: number | string | null
  future: number | string | null
}
/** snapshot scalar. */
export interface SnapshotValue {
  value: number
}
/** snapshot composition (e.g. LCZ) -> labelled parts. */
export interface CompositionValue {
  parts: [string, number][]
}
/** CO₂ sector fingerprint -> labelled sector shares. */
export interface SectorValue {
  sectors: [string, number][]
}

export type ClimateMetricValue
  = | SeriesValue
    | ProjectionValue
    | SnapshotValue
    | CompositionValue
    | SectorValue

/** Full per-city record: metric key -> value shape. Absent metrics are omitted. */
export type ClimateRecord = Record<string, ClimateMetricValue>

/** Headline-only summary: city_id -> { headline key -> latest number }. */
export type ClimateSummary = Record<string, Partial<Record<string, number>>>

// --- Headline keys (mirror catalog HEADLINE_KEYS) ----------------------------

export const HEAT_HEADLINE_KEY = 'heat_warm_days'
export const FLOOD_HEADLINE_KEY = 'flood_100yr_share'
export const SOLAR_HEADLINE_KEY = 'solar_pv_potential'
export const CARBON_HEADLINE_KEY = 'co2_per_capita'
export const CO2_SECTOR_FINGERPRINT_KEY = 'co2_sector_fingerprint'

export const HEADLINE_KEYS = [
  HEAT_HEADLINE_KEY,
  FLOOD_HEADLINE_KEY,
  SOLAR_HEADLINE_KEY,
  CARBON_HEADLINE_KEY
] as const

export type HeadlineKey = (typeof HEADLINE_KEYS)[number]

// --- Lens metadata (section grouping + order) --------------------------------

export const LENS_LABELS: Record<ClimateLens, string> = {
  heat: 'Heat',
  flood: 'Water & flood',
  climate_type: 'Climate type & morphology',
  energy: 'Energy resource',
  footprint: 'Footprint',
  greenness: 'Greenness & livability',
  urban_form: 'Urban form',
  hazard: 'Hazard occurrence'
}

/** Order in which supporting lens groups render below the headline four. */
export const LENS_ORDER: ClimateLens[] = [
  'heat',
  'flood',
  'climate_type',
  'energy',
  'footprint',
  'greenness',
  'urban_form',
  'hazard'
]

/**
 * Supporting (non-headline) metrics for a lens. Excludes the headline metrics
 * (they lead the section) and the sector fingerprint (composed inline under the
 * per-capita CO₂ headline).
 */
export function supportingMetrics(lens: ClimateLens): ClimateMetricDescriptor[] {
  return CLIMATE_METRICS.filter(m => m.lens === lens && !m.headline && !m.sectorFingerprint)
}

// --- Methodology content paths (mirror catalog) ------------------------------

const M_EDGAR = '/data/source-edgar'
const M_SOLAR = '/data/source-solar-atlas'
const M_WIND = '/data/source-wind-atlas'
const M_KOPPEN = '/data/source-koppen'
const M_LCZ = '/data/source-lcz'
const M_C3S = '/data/source-c3s'
const M_EXPOSURE = '/data/source-exposure'
const M_GREENNESS = '/data/source-greenness'
const M_SDG = '/data/source-sdg'
const M_HAZARD = '/data/source-hazard'

// --- The catalog mirror ------------------------------------------------------

export const CLIMATE_METRICS: ClimateMetricDescriptor[] = [
  // Heat
  { key: HEAT_HEADLINE_KEY, label: 'Warm days (TX90p)', lens: 'heat', temporalClass: 'projection', unit: 'days/year', source: 'C3S / CMIP6 (TX90p index)', methodologyPath: M_C3S, modeled: true, headline: true, futureLabel: '2030, SSP5-8.5' },
  { key: 'heat_utci_t32', label: 'Days UTCI > 32 °C', lens: 'heat', temporalClass: 'series', unit: 'days/year', source: 'C3S thermal-comfort (UTCI)', methodologyPath: M_C3S, modeled: true, headline: false },
  { key: 'heat_mean_temp', label: 'Annual mean temperature', lens: 'heat', temporalClass: 'projection', unit: '°C', source: 'C3S / CMIP6 (bioclimatic BIO1)', methodologyPath: M_C3S, modeled: true, headline: false, futureLabel: '2030, RCP8.5' },
  // Flood & water
  { key: FLOOD_HEADLINE_KEY, label: 'Population in 100-yr flood zone', lens: 'flood', temporalClass: 'series', unit: 'share', source: 'GHS-UCDB exposure (100-yr return-period flood model)', methodologyPath: M_EXPOSURE, modeled: true, headline: true },
  { key: 'flood_coastal_lec', label: 'Population ≤10 m coastal elevation', lens: 'flood', temporalClass: 'series', unit: 'share', source: 'GHS-UCDB exposure (low-elevation coastal zone)', methodologyPath: M_EXPOSURE, modeled: true, headline: false },
  { key: 'sea_level_rise', label: 'Local sea-level-rise rate', lens: 'flood', temporalClass: 'snapshot', unit: 'mm/year', source: 'GHS-UCDB water (marine trend)', methodologyPath: M_EXPOSURE, modeled: true, headline: false },
  // Climate type & morphology
  { key: 'koppen_class', label: 'Köppen climate type', lens: 'climate_type', temporalClass: 'projection', unit: null, source: 'Köppen-Geiger (Beck et al. 2018)', methodologyPath: M_KOPPEN, modeled: true, headline: false, futureLabel: '2070, SSP5-8.5', categorical: true },
  { key: 'lcz_composition', label: 'Local Climate Zone composition', lens: 'climate_type', temporalClass: 'snapshot', unit: 'share', source: 'Local Climate Zones (Demuzere et al. 2022)', methodologyPath: M_LCZ, modeled: false, headline: false },
  // Energy resource
  { key: SOLAR_HEADLINE_KEY, label: 'Solar PV potential', lens: 'energy', temporalClass: 'snapshot', unit: 'kWh/kWp', source: 'Global Solar Atlas 2.0 (ESMAP 2020)', methodologyPath: M_SOLAR, modeled: false, headline: true },
  { key: 'wind_speed_100m', label: 'Wind speed @100 m', lens: 'energy', temporalClass: 'snapshot', unit: 'm/s', source: 'Global Wind Atlas (Davis et al. 2023)', methodologyPath: M_WIND, modeled: false, headline: false },
  // Footprint
  { key: CARBON_HEADLINE_KEY, label: 'Per-capita CO₂', lens: 'footprint', temporalClass: 'series', unit: 't CO₂/person', source: 'EDGAR v8.0 (Crippa et al. 2024)', methodologyPath: M_EDGAR, modeled: true, headline: true },
  { key: CO2_SECTOR_FINGERPRINT_KEY, label: 'CO₂ sector fingerprint', lens: 'footprint', temporalClass: 'snapshot', unit: 'share', source: 'EDGAR v8.0 (Crippa et al. 2024)', methodologyPath: M_EDGAR, modeled: true, headline: false, sectorFingerprint: true },
  { key: 'co2_total', label: 'Total CO₂ emissions', lens: 'footprint', temporalClass: 'series', unit: 't CO₂/year', source: 'EDGAR v8.0 (Crippa et al. 2024)', methodologyPath: M_EDGAR, modeled: true, headline: false },
  { key: 'ghg_total', label: 'Total GHG emissions', lens: 'footprint', temporalClass: 'series', unit: 't CO₂-eq/year', source: 'EDGAR v8.0 (Crippa et al. 2024)', methodologyPath: M_EDGAR, modeled: true, headline: false },
  { key: 'pm25_emissions', label: 'PM₂.₅ emissions', lens: 'footprint', temporalClass: 'series', unit: 't/year', source: 'EDGAR v8.0 (Crippa et al. 2024)', methodologyPath: M_EDGAR, modeled: true, headline: false },
  // Urban form
  { key: 'land_use_efficiency', label: 'Land-use efficiency (SDG 11.3.1)', lens: 'urban_form', temporalClass: 'series', unit: 'ratio', source: 'UN-Habitat SDG 11.3.1 (land-consumption / population rate)', methodologyPath: M_SDG, modeled: false, headline: false },
  // Greenness & livability
  { key: 'greenness_built', label: 'High-greenness built-up share', lens: 'greenness', temporalClass: 'series', unit: 'share', source: 'GHS-UCDB greenness (Landsat NDVI)', methodologyPath: M_GREENNESS, modeled: false, headline: false },
  { key: 'greenness_mean', label: 'Mean greenness in built-up', lens: 'greenness', temporalClass: 'series', unit: 'index', source: 'GHS-UCDB greenness (Landsat NDVI)', methodologyPath: M_GREENNESS, modeled: false, headline: false },
  { key: 'green_space_access', label: 'Population with green-space access', lens: 'greenness', temporalClass: 'series', unit: 'share', source: 'GHS-UCDB SDG 11.7 (green-space access)', methodologyPath: M_GREENNESS, modeled: false, headline: false },
  { key: 'canopy_height', label: 'Mean tree-canopy height', lens: 'greenness', temporalClass: 'snapshot', unit: 'm', source: 'GHS-UCDB canopy height (Lang et al.)', methodologyPath: M_GREENNESS, modeled: false, headline: false },
  // Hazard occurrence
  { key: 'wildfire_burnt_area', label: 'Wildfire burnt area', lens: 'hazard', temporalClass: 'series', unit: 'ha/year', source: 'GHS-UCDB hazard (burnt-area record)', methodologyPath: M_HAZARD, modeled: false, headline: false },
  { key: 'heatwave_events', label: 'Heatwave events', lens: 'hazard', temporalClass: 'snapshot', unit: 'count', source: 'GHS-UCDB hazard (climate-event counts)', methodologyPath: M_HAZARD, modeled: true, headline: false },
  { key: 'drought_events', label: 'Drought events', lens: 'hazard', temporalClass: 'snapshot', unit: 'count', source: 'GHS-UCDB hazard (climate-event counts)', methodologyPath: M_HAZARD, modeled: true, headline: false }
]

const METRICS_BY_KEY = new Map(CLIMATE_METRICS.map(m => [m.key, m]))

export function getMetricDescriptor(key: string): ClimateMetricDescriptor | undefined {
  return METRICS_BY_KEY.get(key)
}

export function headlineMetrics(): ClimateMetricDescriptor[] {
  return HEADLINE_KEYS.map(k => METRICS_BY_KEY.get(k)!).filter(Boolean)
}

export function metricsForLens(lens: ClimateLens): ClimateMetricDescriptor[] {
  return CLIMATE_METRICS.filter(m => m.lens === lens)
}

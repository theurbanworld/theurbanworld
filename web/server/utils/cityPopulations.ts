/**
 * Server-side city population stats with in-memory caching.
 *
 * Fetches city_populations_h3_r8.json from R2 once and caches a compact
 * Map of each city's current-epoch (2025) stats — population, area, and
 * density — for O(1) lookups. Used by the city metadata API route so that
 * pages can render OG-image stats server-side WITHOUT loading the full
 * ~14 MB populations dataset into the SSR hydration payload.
 *
 * Only the 2025 epoch is retained; the full timeseries is discarded after
 * parsing, keeping the cached structure small.
 */

export interface CityPopulationStats {
  population: number
  area_km2: number
  density_per_km2: number
}

interface PopulationEpoch {
  population: number
  area_km2: number
  density_per_km2: number
}

interface PopulationRecord {
  city_id: string
  epochs: Record<string, PopulationEpoch>
}

/** Epoch used for OG/SEO "current" stats. */
const STATS_EPOCH = '2025'
const POPULATIONS_URL = 'https://data.theurban.world/data/city_populations_h3_r8.json'
const CACHE_TTL_MS = 60 * 60 * 1000 // 1 hour

let cachedMap: Map<string, CityPopulationStats> | null = null
let cacheTimestamp = 0

function getDataUrl(): string {
  const config = useRuntimeConfig()
  const r2BaseUrl = config.public.r2BaseUrl
  if (r2BaseUrl) {
    return `${r2BaseUrl}/data/city_populations_h3_r8.json`
  }
  return POPULATIONS_URL
}

async function ensureCache(): Promise<void> {
  const now = Date.now()
  if (cachedMap && (now - cacheTimestamp) < CACHE_TTL_MS) {
    return
  }

  const records = await $fetch<PopulationRecord[]>(getDataUrl())

  const map = new Map<string, CityPopulationStats>()
  for (const record of records) {
    const epoch = record.epochs?.[STATS_EPOCH]
    if (epoch) {
      map.set(record.city_id, {
        population: epoch.population,
        area_km2: epoch.area_km2,
        density_per_km2: epoch.density_per_km2
      })
    }
  }

  cachedMap = map
  cacheTimestamp = now
}

/**
 * Get the current-epoch (2025) population stats for a single city.
 * Returns undefined if the city or its 2025 epoch is missing.
 */
export async function getCityStats(id: string): Promise<CityPopulationStats | undefined> {
  try {
    await ensureCache()
    return cachedMap!.get(id)
  } catch {
    // Populations data unavailable — pages degrade gracefully (no OG stats).
    return undefined
  }
}

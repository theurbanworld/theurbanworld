/**
 * City Climate & Energy data loading
 *
 * Loads two kinds of R2 artifact (the summary/detail split):
 *   - climate_summary.json — headline-four latest values for every covered city
 *     (rankings, distribution strips, comparison). Small (~1 MB); loaded once.
 *   - climate/{city_id}.json — the full per-metric ClimateRecord for one city
 *     (the city section). Fetched on demand and cached, matching the per-city
 *     city_cells pattern (the full profile is ~26 MB, too large to fetch whole).
 *
 * Partial coverage is the norm: UCDB covers ~11.4k of ~13k centres, and marine
 * metrics are inland-NULL. A city absent from the data yields null without error
 * (the useCityPopulations 404 precedent), so the section/rankings/comparison
 * render the "not available" state rather than throwing.
 *
 * Mirror: pipeline/src/climate/catalog.py via web/types/climate.ts.
 */

import type { ClimateRecord, ClimateSummary, HEADLINE_KEYS } from '../../types/climate'

// Module-level per-city profile cache, shared across all callers. A key present
// with value null means "fetched, not covered" (so we don't refetch).
const profileCache = reactive<Record<string, ClimateRecord | null>>({})
const inflight = new Set<string>()

/** Test-only: clear the module-level per-city profile cache between tests. */
export function __clearClimateProfileCache(): void {
  // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
  for (const key of Object.keys(profileCache)) delete profileCache[key]
  inflight.clear()
}

function r2Url(runtimeConfig: ReturnType<typeof useRuntimeConfig>, file: string): string {
  const base = runtimeConfig.public.r2BaseUrl || 'https://data.theurban.world'
  return `${base}/data/${file}`
}

async function fetchOrEmpty<T extends object>(url: string, empty: T): Promise<T> {
  try {
    return (await $fetch(url)) as T
  } catch (e: unknown) {
    // 404/empty degrades to empty, not error — data may not be deployed yet.
    if (e && typeof e === 'object' && 'statusCode' in e && e.statusCode === 404) {
      return empty
    }
    throw e
  }
}

export function useCityClimate() {
  const runtimeConfig = useRuntimeConfig()

  // Summary — headline values for every covered city (rankings/distribution).
  const summaryReq = useAsyncData<ClimateSummary>(
    'climate-summary',
    () => fetchOrEmpty<ClimateSummary>(r2Url(runtimeConfig, 'climate_summary.json'), {}),
    { immediate: false, server: false, default: () => ({}) }
  )

  /** Set of cities with any climate coverage (from summary) — for ranking/distribution subsets. */
  const climateCities = computed<Set<string>>(() => {
    const summary = summaryReq.data.value
    return new Set(summary ? Object.keys(summary) : [])
  })

  /** Fetch (and cache) one city's full profile. 404 caches null, not an error. */
  async function loadCityProfile(cityId: string): Promise<void> {
    if (cityId in profileCache || inflight.has(cityId)) return
    inflight.add(cityId)
    try {
      const record = await $fetch<ClimateRecord>(r2Url(runtimeConfig, `climate/${cityId}.json`))
      profileCache[cityId] = record ?? null
    } catch {
      // Absent city (404) or fetch failure -> mark as not covered, render gracefully.
      profileCache[cityId] = null
    } finally {
      inflight.delete(cityId)
    }
  }

  /** Full climate record for a city, or null if absent / not yet loaded. */
  function getClimate(cityId: string): ClimateRecord | null {
    return profileCache[cityId] ?? null
  }

  /** Whether a city's profile fetch has resolved (covered or not). */
  function isCityLoaded(cityId: string): boolean {
    return cityId in profileCache
  }

  /** A single headline latest value for a city, or undefined if absent. */
  function getHeadline(cityId: string, key: (typeof HEADLINE_KEYS)[number]): number | undefined {
    return summaryReq.data.value?.[cityId]?.[key]
  }

  /** Whether a city has any climate coverage (summary or a loaded non-null profile). */
  function hasCityClimate(cityId: string): boolean {
    if (summaryReq.data.value && cityId in summaryReq.data.value) return true
    return Boolean(profileCache[cityId])
  }

  return {
    /** Load the headline summary (rankings/distribution). */
    loadSummary: summaryReq.execute,
    /** Fetch + cache one city's full profile (city section). */
    loadCityProfile,
    summaryStatus: readonly(summaryReq.status),
    /** Raw summary map, for distribution/ranking computations. */
    summary: summaryReq.data as Readonly<Ref<ClimateSummary | null>>,
    climateCities,
    getClimate,
    isCityLoaded,
    getHeadline,
    hasCityClimate
  }
}

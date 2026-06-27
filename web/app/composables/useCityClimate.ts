/**
 * City Climate & Energy data loading
 *
 * Loads two R2 artifacts (the governance summary/detail split):
 *   - climate_summary.json — headline-four latest values per city (rankings,
 *     distribution strips). Small; loaded eagerly on demand.
 *   - climate_profile.json — full per-metric ClimateRecord per city (the city
 *     section). Larger; loaded on demand when a city page needs it.
 *
 * Partial coverage is the norm: UCDB covers ~11.4k of ~13k centres, and marine
 * metrics are inland-NULL. A city absent from the data yields null without error
 * (the useCityPopulations 404 precedent), so the section/rankings/comparison
 * render the "not available" state rather than throwing.
 *
 * Mirror: pipeline/src/climate/catalog.py via web/types/climate.ts.
 */

import type { ClimateRecord, ClimateSummary, HEADLINE_KEYS } from '../../types/climate'

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

  // Profile — full per-metric records (the city section). Client-only, larger.
  const profileReq = useAsyncData<Record<string, ClimateRecord>>(
    'climate-profile',
    () =>
      fetchOrEmpty<Record<string, ClimateRecord>>(
        r2Url(runtimeConfig, 'climate_profile.json'),
        {}
      ),
    { immediate: false, server: false, default: () => ({}) }
  )

  /** Set of cities with any climate coverage (from summary) — for ranking/distribution subsets. */
  const climateCities = computed<Set<string>>(() => {
    const summary = summaryReq.data.value
    return new Set(summary ? Object.keys(summary) : [])
  })

  /** Full climate record for a city, or null if absent / not yet loaded. */
  function getClimate(cityId: string): ClimateRecord | null {
    return profileReq.data.value?.[cityId] ?? null
  }

  /** A single headline latest value for a city, or undefined if absent. */
  function getHeadline(cityId: string, key: (typeof HEADLINE_KEYS)[number]): number | undefined {
    return summaryReq.data.value?.[cityId]?.[key]
  }

  /** Whether a city has any climate coverage (summary or loaded profile). */
  function hasCityClimate(cityId: string): boolean {
    if (summaryReq.data.value && cityId in summaryReq.data.value) return true
    return Boolean(profileReq.data.value && cityId in profileReq.data.value)
  }

  return {
    /** Load the headline summary (rankings/distribution). */
    loadSummary: summaryReq.execute,
    /** Load the full per-city profile (city section). */
    loadProfile: profileReq.execute,
    summaryStatus: readonly(summaryReq.status),
    profileStatus: readonly(profileReq.status),
    isLoadingProfile: computed(() => profileReq.status.value === 'pending'),
    error: readonly(profileReq.error),
    /** Raw summary map, for distribution/ranking computations. */
    summary: summaryReq.data as Readonly<Ref<ClimateSummary | null>>,
    climateCities,
    getClimate,
    getHeadline,
    hasCityClimate
  }
}

/**
 * Radial density profile data loading
 *
 * Loads radial_profiles_h3_r8.json from R2 and provides
 * methods for looking up density arrays by city and epoch.
 *
 * Data format: Record<city_id, Record<epoch, (number | null)[]>>
 * Each array = density_per_km2 per ring (index = ring_index)
 */

import type { YearEpoch } from '../../types/h3'

type RadialProfileData = Record<string, Record<string, (number | null)[]>>

export function useRadialProfiles() {
  const runtimeConfig = useRuntimeConfig()

  function getDataUrl(): string {
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    if (r2BaseUrl) {
      return `${r2BaseUrl}/data/radial_profiles_h3_r8.json`
    }
    return 'https://data.theurban.world/data/radial_profiles_h3_r8.json'
  }

  const { data, status, error, execute } = useAsyncData<RadialProfileData>(
    'radial-profiles',
    async () => {
      try {
        return await $fetch<RadialProfileData>(getDataUrl())
      } catch (e: unknown) {
        if (e && typeof e === 'object' && 'statusCode' in e && e.statusCode === 404) {
          return {}
        }
        throw e
      }
    },
    {
      immediate: false,
      // Client-only: this dataset covers ALL cities (~4.5 MB) and is only used
      // by .client.vue components (map, radial chart). With server: true it was
      // fetched during SSR and serialized into the hydration payload, bloating
      // every city/compare page's HTML past 5 MB.
      server: false,
      default: () => ({})
    }
  )

  const isLoading = computed(() => status.value === 'pending')
  const isLoaded = computed(() => status.value === 'success')

  /**
   * Get density array for a city at a specific epoch
   */
  function getProfile(cityId: string, epoch: YearEpoch): (number | null)[] | null {
    if (!data.value) return null
    return data.value[cityId]?.[String(epoch)] ?? null
  }

  /**
   * Get max density value for a city at an epoch (for Y-axis scaling)
   */
  function getMaxDensity(cityId: string, epoch: YearEpoch): number {
    const profile = getProfile(cityId, epoch)
    if (!profile) return 0
    let max = 0
    for (const v of profile) {
      if (v != null && v > max) max = v
    }
    return max
  }

  return {
    status: readonly(status),
    isLoading,
    isLoaded,
    error: readonly(error),
    execute,
    getProfile,
    getMaxDensity
  }
}

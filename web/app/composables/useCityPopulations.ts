/**
 * City population data loading by epoch
 *
 * Uses Nuxt's useAsyncData for SSR-compatible data fetching.
 * Loads city population timeseries data from JSON and provides
 * methods for looking up population, area, and density by city and epoch.
 *
 * Data structure per city includes population, area_km2, and density_per_km2
 * for each epoch year (1975-2030).
 */

import type { YearEpoch } from '../../types/h3'
import { useDataSource } from './useDataSource'

/**
 * City population data for a single epoch
 */
export interface CityPopulationEpoch {
  population: number
  area_km2: number
  density_per_km2: number
}

/**
 * City population timeseries record
 */
export interface CityPopulationRecord {
  city_id: string
  epochs: Record<YearEpoch, CityPopulationEpoch>
}

export function useCityPopulations() {
  const runtimeConfig = useRuntimeConfig()
  const { sourceSlug } = useDataSource()

  /**
   * Get the data URL for the current data source
   */
  function getDataUrl(): string {
    const slug = sourceSlug.value
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    if (r2BaseUrl) {
      return `${r2BaseUrl}/data/city_populations_${slug}.json`
    }
    return `https://data.theurban.world/data/city_populations_${slug}.json`
  }

  // useAsyncData with unique key for deduplication and SSR
  const { data, status, error, execute, refresh } = useAsyncData<CityPopulationRecord[]>(
    'city-populations',
    async () => {
      try {
        return await $fetch<CityPopulationRecord[]>(getDataUrl())
      } catch (e: unknown) {
        // Handle 404 gracefully - data may not be deployed
        if (e && typeof e === 'object' && 'statusCode' in e && e.statusCode === 404) {
          console.warn('City populations data not found, using fallback')
          return []
        }
        throw e
      }
    },
    {
      immediate: false, // Don't auto-fetch, trigger on-demand
      server: false, // Client-only — avoids serializing large dataset into SSR payload
      default: () => [],
      watch: [sourceSlug] // Re-fetch when data source changes
    }
  )

  // Build Map from data for synchronous lookups
  const populationsMapRef = computed(() => {
    if (!data.value?.length) return null
    return new Map(data.value.map(r => [r.city_id, r.epochs]))
  })

  // Computed states
  const isLoading = computed(() => status.value === 'pending')
  const isLoaded = computed(() => status.value === 'success')

  /**
   * Get population data for a city at a specific epoch
   *
   * @param cityId - City ID to look up
   * @param epoch - Year epoch (1975-2030)
   * @returns Population data or undefined if not found
   */
  function getCityPopulationData(cityId: string, epoch: YearEpoch): CityPopulationEpoch | undefined {
    return populationsMapRef.value?.get(cityId)?.[epoch]
  }

  /**
   * Get all epoch data for a city
   *
   * @param cityId - City ID to look up
   * @returns All epoch data or undefined if not found
   */
  function getCityAllEpochs(cityId: string): Record<YearEpoch, CityPopulationEpoch> | undefined {
    return populationsMapRef.value?.get(cityId)
  }

  /**
   * Check if population data exists for a city
   *
   * @param cityId - City ID to check
   * @returns true if data exists
   */
  function hasCity(cityId: string): boolean {
    return populationsMapRef.value?.has(cityId) ?? false
  }

  /**
   * Check if data has been loaded
   */
  function hasData(): boolean {
    return populationsMapRef.value !== null && populationsMapRef.value.size > 0
  }

  return {
    /** Loading status from useAsyncData */
    status: readonly(status),
    /** Whether data is currently loading */
    isLoading,
    /** Whether data has been loaded (may be empty if 404) */
    isLoaded,
    /** Error if loading failed */
    error: readonly(error),
    /** Trigger data loading (SSR-compatible) */
    execute,
    /** Force refresh data */
    refresh,
    /** Get population data for a city at a specific epoch */
    getCityPopulationData,
    /** Get all epoch data for a city */
    getCityAllEpochs,
    /** Check if city data exists */
    hasCity,
    /** Check if any data is available */
    hasData,
    /** Read-only populations map for distribution calculations */
    populationsMap: populationsMapRef as Readonly<ComputedRef<Map<string, Record<YearEpoch, CityPopulationEpoch>> | null>>
  }
}

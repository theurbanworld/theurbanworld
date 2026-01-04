/**
 * City population data loading by epoch
 *
 * Loads city population timeseries data from JSON and provides
 * methods for looking up population, area, and density by city and epoch.
 *
 * Data structure per city includes population, area_km2, and density_per_km2
 * for each epoch year (1975-2030).
 */

import type { YearEpoch } from '../../types/h3'

// Data URL for city populations JSON
const CITY_POPULATIONS_URL = 'https://data.theurban.world/data/city_populations.json'

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

// Singleton state for city populations data
let populationsMap: Map<string, Record<YearEpoch, CityPopulationEpoch>> | null = null
let loadPromise: Promise<void> | null = null

const isLoading = ref(false)
const error = ref<Error | null>(null)
const isLoaded = ref(false)

export function useCityPopulations() {
  const runtimeConfig = useRuntimeConfig()

  /**
   * Get the data URL, preferring R2 if configured
   */
  function getDataUrl(): string {
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    if (r2BaseUrl) {
      return `${r2BaseUrl}/data/city_populations.json`
    }
    return CITY_POPULATIONS_URL
  }

  /**
   * Load the city populations JSON file
   */
  async function loadData(): Promise<void> {
    // If already loading, wait for existing promise
    if (loadPromise) {
      return loadPromise
    }

    // If already loaded, return immediately
    if (populationsMap) {
      return
    }

    isLoading.value = true
    error.value = null

    loadPromise = (async () => {
      try {
        const dataUrl = getDataUrl()
        const response = await fetch(dataUrl)

        if (!response.ok) {
          // If 404, data isn't deployed yet - that's OK, we'll fall back to cities index
          if (response.status === 404) {
            console.warn('City populations data not found, using fallback')
            populationsMap = new Map()
            isLoaded.value = true
            return
          }
          throw new Error(`Failed to fetch city populations: ${response.status}`)
        }

        const data: CityPopulationRecord[] = await response.json()

        // Build lookup map by city_id
        populationsMap = new Map()
        for (const record of data) {
          populationsMap.set(record.city_id, record.epochs)
        }

        isLoaded.value = true
        console.log(`Loaded city populations for ${populationsMap.size} cities`)
      } catch (e) {
        console.error('Failed to load city populations:', e)
        // On error, set an empty map so we can use fallback
        populationsMap = new Map()
        error.value = e instanceof Error ? e : new Error('Failed to load city populations')
        isLoaded.value = true
      } finally {
        isLoading.value = false
        loadPromise = null
      }
    })()

    return loadPromise
  }

  /**
   * Get population data for a city at a specific epoch
   *
   * @param cityId - City ID to look up
   * @param epoch - Year epoch (1975-2030)
   * @returns Population data or undefined if not found
   */
  function getCityPopulationData(cityId: string, epoch: YearEpoch): CityPopulationEpoch | undefined {
    return populationsMap?.get(cityId)?.[epoch]
  }

  /**
   * Get all epoch data for a city
   *
   * @param cityId - City ID to look up
   * @returns All epoch data or undefined if not found
   */
  function getCityAllEpochs(cityId: string): Record<YearEpoch, CityPopulationEpoch> | undefined {
    return populationsMap?.get(cityId)
  }

  /**
   * Check if population data exists for a city
   *
   * @param cityId - City ID to check
   * @returns true if data exists
   */
  function hasCity(cityId: string): boolean {
    return populationsMap?.has(cityId) ?? false
  }

  /**
   * Check if data has been loaded
   */
  function hasData(): boolean {
    return populationsMap !== null && populationsMap.size > 0
  }

  return {
    /** Whether data is currently loading */
    isLoading: readonly(isLoading),
    /** Error if loading failed */
    error: readonly(error),
    /** Whether data has been loaded (may be empty if 404) */
    isLoaded: readonly(isLoaded),
    /** Load the city populations data (call once on app start) */
    loadData,
    /** Get population data for a city at a specific epoch */
    getCityPopulationData,
    /** Get all epoch data for a city */
    getCityAllEpochs,
    /** Check if city data exists */
    hasCity,
    /** Check if any data is available */
    hasData
  }
}

/**
 * Cities index data loading and lookup
 *
 * Uses Nuxt's useAsyncData for SSR-compatible data fetching.
 * Loads the cities_index.json file to provide city name lookup
 * by city_id. Used for hover tooltips on city boundaries.
 */

// Data URL for cities index
const CITIES_INDEX_URL = 'https://data.theurban.world/data/cities_index.json'

/**
 * City index entry structure from cities_index.json
 */
export interface CityIndexEntry {
  id: string
  name: string
  country: string
  country_code: string
  centroid: [number, number]
  bbox: [number, number, number, number]
  population: number
  wikidata_id?: string
  birth_year?: number
  death_year?: number
}

export function useCitiesIndex() {
  const runtimeConfig = useRuntimeConfig()

  /**
   * Get the data URL, preferring R2 if configured
   */
  function getDataUrl(): string {
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    if (r2BaseUrl) {
      return `${r2BaseUrl}/data/cities_index.json`
    }
    return CITIES_INDEX_URL
  }

  // useAsyncData with unique key for deduplication and SSR
  const { data, status, error, execute, refresh } = useAsyncData<CityIndexEntry[]>(
    'cities-index',
    () => $fetch<CityIndexEntry[]>(getDataUrl()),
    {
      immediate: false, // Don't auto-fetch, trigger on-demand
      server: false, // Client-only — avoids serializing large dataset into SSR payload
      default: () => []
    }
  )

  // Build Map from data for synchronous lookups
  const citiesMapRef = computed(() => {
    if (!data.value?.length) return null
    return new Map(data.value.map(city => [city.id, city]))
  })

  // Computed states
  const isLoading = computed(() => status.value === 'pending')
  const isLoaded = computed(() => status.value === 'success' && !!data.value?.length)

  /**
   * Get city by ID
   *
   * @param cityId - City ID to look up
   * @returns City entry or undefined if not found
   */
  function getCity(cityId: string): CityIndexEntry | undefined {
    return citiesMapRef.value?.get(cityId)
  }

  /**
   * Get city name by ID
   *
   * @param cityId - City ID to look up
   * @returns City name or undefined if not found
   */
  function getCityName(cityId: string): string | undefined {
    return citiesMapRef.value?.get(cityId)?.name
  }

  /**
   * Check if a city exists in the index
   *
   * @param cityId - City ID to check
   * @returns true if city exists
   */
  function hasCity(cityId: string): boolean {
    return citiesMapRef.value?.has(cityId) ?? false
  }

  // Expose all cities for fuse.js search (future)
  const allCities = computed(() => data.value ?? [])

  return {
    /** Loading status from useAsyncData */
    status: readonly(status),
    /** Whether the index is currently loading */
    isLoading,
    /** Whether the index has been successfully loaded */
    isLoaded,
    /** Error if loading failed */
    error: readonly(error),
    /** Trigger data loading (SSR-compatible) */
    execute,
    /** Force refresh data */
    refresh,
    /** Get city by ID */
    getCity,
    /** Get city name by ID */
    getCityName,
    /** Check if city exists */
    hasCity,
    /** All cities array for search */
    allCities
  }
}

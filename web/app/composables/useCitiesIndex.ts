/**
 * Cities index data loading and lookup
 *
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
}

// Singleton state for cities index
let citiesMap: Map<string, CityIndexEntry> | null = null
let loadPromise: Promise<void> | null = null

const isLoading = ref(false)
const error = ref<Error | null>(null)
const isLoaded = ref(false)

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

  /**
   * Load the cities index JSON file
   */
  async function loadIndex(): Promise<void> {
    // If already loading, wait for existing promise
    if (loadPromise) {
      return loadPromise
    }

    // If already loaded, return immediately
    if (citiesMap) {
      return
    }

    isLoading.value = true
    error.value = null

    loadPromise = (async () => {
      try {
        const dataUrl = getDataUrl()
        const response = await fetch(dataUrl)

        if (!response.ok) {
          throw new Error(`Failed to fetch cities index: ${response.status}`)
        }

        const data: CityIndexEntry[] = await response.json()

        // Build lookup map by city_id
        citiesMap = new Map()
        for (const city of data) {
          citiesMap.set(city.id, city)
        }

        isLoaded.value = true
        console.log(`Loaded cities index with ${citiesMap.size} cities`)
      } catch (e) {
        console.error('Failed to load cities index:', e)
        error.value = e instanceof Error ? e : new Error('Failed to load cities index')
        throw error.value
      } finally {
        isLoading.value = false
        loadPromise = null
      }
    })()

    return loadPromise
  }

  /**
   * Get city by ID
   *
   * @param cityId - City ID to look up
   * @returns City entry or undefined if not found
   */
  function getCity(cityId: string): CityIndexEntry | undefined {
    return citiesMap?.get(cityId)
  }

  /**
   * Get city name by ID
   *
   * @param cityId - City ID to look up
   * @returns City name or undefined if not found
   */
  function getCityName(cityId: string): string | undefined {
    return citiesMap?.get(cityId)?.name
  }

  /**
   * Check if a city exists in the index
   *
   * @param cityId - City ID to check
   * @returns true if city exists
   */
  function hasCity(cityId: string): boolean {
    return citiesMap?.has(cityId) ?? false
  }

  return {
    /** Whether the index is currently loading */
    isLoading: readonly(isLoading),
    /** Error if loading failed */
    error: readonly(error),
    /** Whether the index has been successfully loaded */
    isLoaded: readonly(isLoaded),
    /** Load the cities index (call once on app start) */
    loadIndex,
    /** Get city by ID */
    getCity,
    /** Get city name by ID */
    getCityName,
    /** Check if city exists */
    hasCity
  }
}

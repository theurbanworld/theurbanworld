/**
 * H3 hexagon data loading from Parquet
 *
 * Loads the full h3_r8_pop_timeseries.parquet file and provides
 * methods for filtering by year. Data is stored in memory for
 * instant year switching.
 */

import { load } from '@loaders.gl/core'
import { ParquetLoader } from '@loaders.gl/parquet'
import { getPopulationColumnKey, type YearEpoch, type H3Hexagon } from '../../types/h3'

// Data URL for H3 population timeseries
const H3_DATA_URL = 'https://data.theurban.world/data/h3_r8_pop_timeseries.parquet'

// Store raw data with all years in memory (singleton)
interface H3RawData {
  h3Indices: string[] // Pre-converted to hex strings
  populationByYear: Map<YearEpoch, Float64Array>
}

// Singleton state
let rawDataCache: H3RawData | null = null
let loadPromise: Promise<void> | null = null

const isLoading = ref(false)
const loadProgress = ref(0)
const error = ref<Error | null>(null)
const isDataLoaded = ref(false)

export function useH3Data() {
  /**
   * Get the data URL
   */
  function getDataUrl(): string {
    return H3_DATA_URL
  }

  /**
   * Load the parquet file and parse into memory
   */
  async function loadData(): Promise<void> {
    // If already loading, wait for existing promise
    if (loadPromise) {
      return loadPromise
    }

    // If already loaded, return immediately
    if (rawDataCache) {
      return
    }

    isLoading.value = true
    loadProgress.value = 0
    error.value = null

    loadPromise = (async () => {
      try {
        const dataUrl = getDataUrl()

        // Load parquet file using loaders.gl
        // The ParquetLoader returns a table object
        const result = await load(dataUrl, ParquetLoader, {
          parquet: {
            // Return as array of row objects
            shape: 'object-row-table'
          }
        })

        // Progress update - file loaded, now processing
        loadProgress.value = 50

        // Extract data from the loaded result
        // The result structure varies - check for data property first
        let rows: unknown[]
        if (result && typeof result === 'object' && 'data' in result && Array.isArray(result.data)) {
          rows = result.data
        } else if (Array.isArray(result)) {
          rows = result
        } else {
          throw new Error('Unexpected parquet data format')
        }

        if (rows.length === 0) {
          throw new Error('No data found in parquet file')
        }

        // Initialize storage
        const h3Indices: string[] = []
        const populationByYear = new Map<YearEpoch, Float64Array>()

        // Pre-allocate Float64Arrays for each year
        const years: YearEpoch[] = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
        for (const year of years) {
          populationByYear.set(year, new Float64Array(rows.length))
        }

        // Process each row
        for (let i = 0; i < rows.length; i++) {
          const row = rows[i] as Record<string, unknown>

          // h3_index is stored as hex string in parquet
          // loaders.gl may return it as string or as an object with toString()
          const rawH3Index = row.h3_index
          let h3Index: string
          if (typeof rawH3Index === 'string') {
            h3Index = rawH3Index
          } else if (rawH3Index && typeof rawH3Index === 'object' && 'toString' in rawH3Index) {
            h3Index = String(rawH3Index)
          } else {
            console.warn(`Unexpected h3_index type at row ${i}:`, typeof rawH3Index, rawH3Index)
            continue
          }

          h3Indices.push(h3Index)

          // Extract population for each year
          for (const year of years) {
            const columnKey = getPopulationColumnKey(year)
            const popValue = row[columnKey]
            const popArray = populationByYear.get(year)
            if (popArray) {
              popArray[i] = typeof popValue === 'number' && !isNaN(popValue) ? popValue : 0
            }
          }

          // Update progress periodically
          if (i % 50000 === 0) {
            loadProgress.value = 50 + Math.round((i / rows.length) * 50)
          }
        }

        // Store in cache
        rawDataCache = {
          h3Indices,
          populationByYear
        }

        loadProgress.value = 100
        isDataLoaded.value = true

        console.log(`Loaded ${h3Indices.length} H3 hexagons with population data`)
      } catch (e) {
        console.error('Failed to load H3 data:', e)
        error.value = e instanceof Error ? e : new Error('Failed to load H3 data')
        throw error.value
      } finally {
        isLoading.value = false
        loadPromise = null
      }
    })()

    return loadPromise
  }

  /**
   * Get H3 hexagon data filtered for a specific year
   * Returns array of objects suitable for deck.gl H3HexagonLayer
   *
   * @param year - Year epoch to filter for
   * @returns Array of H3Hexagon objects with h3Index and population
   */
  function getDataForYear(year: YearEpoch): H3Hexagon[] {
    if (!rawDataCache) {
      return []
    }

    const { h3Indices, populationByYear } = rawDataCache
    const populations = populationByYear.get(year)

    if (!populations) {
      console.warn(`No population data for year ${year}`)
      return []
    }

    // Build array of hexagons with non-zero population
    const result: H3Hexagon[] = []

    for (let i = 0; i < h3Indices.length; i++) {
      const population = populations[i]
      const h3Index = h3Indices[i]
      // Only include hexagons with positive population and valid index
      if (h3Index !== undefined && population !== undefined && population > 0) {
        result.push({
          h3Index,
          population
        })
      }
    }

    return result
  }

  /**
   * Get the total number of hexagons loaded
   */
  function getHexagonCount(): number {
    return rawDataCache?.h3Indices.length ?? 0
  }

  /**
   * Check if data has been loaded
   */
  function hasData(): boolean {
    return rawDataCache !== null
  }

  return {
    /** Whether data is currently loading */
    isLoading: readonly(isLoading),
    /** Loading progress (0-100) */
    loadProgress: readonly(loadProgress),
    /** Error if loading failed */
    error: readonly(error),
    /** Whether data has been successfully loaded */
    isDataLoaded: readonly(isDataLoaded),
    /** Load the parquet data (call once on app start) */
    loadData,
    /** Get hexagon data filtered for a specific year */
    getDataForYear,
    /** Get total hexagon count */
    getHexagonCount,
    /** Check if data is available */
    hasData
  }
}

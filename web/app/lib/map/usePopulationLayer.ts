/**
 * Per-city population heatmap layer
 *
 * Creates a deck.gl H3HexagonLayer showing a single city's H3 cells
 * colored by population using the sepia logarithmic scale. Loads per-city
 * JSON files on demand from R2 (city_h3/{city_id}.json).
 *
 * JSON format: {"cells": [{"h": "882f...", "p": [pop_1975, ..., pop_2030]}]}
 */

import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { Layer } from '@deck.gl/core'
import type { H3Hexagon, YearEpoch } from '~~/types/h3'
import { YEAR_EPOCHS } from '~~/types/h3'
import { getColorForPopulation } from '~/utils/colorScale'

/** Raw cell from the per-city JSON */
interface CityH3Cell {
  h: string
  p: number[] // 12 elements, one per epoch (1975-2030)
}

interface CityH3Data {
  cells: CityH3Cell[]
}

export interface UsePopulationLayerOptions {
  /** Whether dark mode is enabled */
  isDarkMode?: Ref<boolean> | boolean
}

// Cache: one city at a time
let cachedCityId: string | null = null
let cachedData: CityH3Data | null = null

export function usePopulationLayer(options: UsePopulationLayerOptions = {}) {
  const runtimeConfig = useRuntimeConfig()
  const { selectedCityId } = useCitySelection()
  const { selectedYear } = useSelectedYear()
  const { isPopulationLayerActive, isLoadingH3 } = usePopulationHighlight()

  const isDarkMode = computed(() => {
    const mode = options.isDarkMode
    if (typeof mode === 'boolean') return mode
    if (mode && 'value' in mode) return mode.value
    return false
  })

  const cityHexagons = ref<H3Hexagon[]>([])

  function getCityH3Url(cityId: string): string {
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    const base = r2BaseUrl || 'https://data.theurban.world'
    return `${base}/data/city_h3/${cityId}.json`
  }

  async function loadCityData(cityId: string): Promise<CityH3Data> {
    if (cachedCityId === cityId && cachedData) {
      return cachedData
    }

    const data = await $fetch<CityH3Data>(getCityH3Url(cityId))
    cachedCityId = cityId
    cachedData = data
    return data
  }

  function getHexagonsForYear(data: CityH3Data, year: YearEpoch): H3Hexagon[] {
    const epochIndex = YEAR_EPOCHS.indexOf(year)
    if (epochIndex < 0) return []

    const result: H3Hexagon[] = []
    for (const cell of data.cells) {
      const population = cell.p[epochIndex]
      if (population !== undefined && population > 0) {
        result.push({ h3Index: cell.h, population })
      }
    }
    return result
  }

  // Load per-city data and extract year when layer is activated
  watch(
    [isPopulationLayerActive, selectedCityId, selectedYear],
    async ([active, cityId, year]) => {
      if (!active || !cityId) {
        cityHexagons.value = []
        return
      }

      isLoadingH3.value = true
      try {
        const data = await loadCityData(cityId)
        cityHexagons.value = getHexagonsForYear(data, year as YearEpoch)
        console.log(`[PopulationLayer] City ${cityId}: ${cityHexagons.value.length} cells for ${year}`)
      } catch (e) {
        console.error(`[PopulationLayer] Failed to load city ${cityId}:`, e)
        cityHexagons.value = []
      } finally {
        isLoadingH3.value = false
      }
    },
    { immediate: true }
  )

  const layer = computed<Layer | null>(() => {
    if (cityHexagons.value.length === 0) return null

    const darkMode = isDarkMode.value

    return new H3HexagonLayer({
      id: 'city-population-layer',
      // Render beneath the city boundary line so the outline stays visible
      // above the population numbers (interleaved deck.gl + MapLibre).
      beforeId: 'city-boundaries-line',
      data: cityHexagons.value,
      getHexagon: (d: H3Hexagon) => d.h3Index,
      getFillColor: (d: H3Hexagon) => getColorForPopulation(d.population, darkMode),
      extruded: false,
      coverage: 1,
      opacity: 0.85,
      stroked: false,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 80],
      updateTriggers: {
        getFillColor: [darkMode]
      }
    }) as unknown as Layer
  })

  return {
    layer,
    cityHexagons: readonly(cityHexagons)
  }
}

/**
 * Radial density map layer
 *
 * Creates a deck.gl H3HexagonLayer showing a city's H3 cells
 * colored by ring distance from centroid. Loads cell indices
 * on-demand per city from R2 (tiny JSON files, ~1-150KB each).
 */

import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { Layer } from '@deck.gl/core'
import { cellToLatLng } from 'h3-js'
import { getRingColorRGBA } from '~/utils/radialColors'

interface RadialHexagon {
  h3Index: string
  ringIndex: number
}

/**
 * Haversine distance in km between two lat/lng points
 */
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180)
    * Math.cos(lat2 * Math.PI / 180)
    * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// Cache fetched cell indices per city
const cellsCache = new Map<string, string[]>()

export function useRadialLayer() {
  const runtimeConfig = useRuntimeConfig()
  const { selectedYear: _selectedYear } = useSelectedYear()
  const { selectedCityId } = useCitySelection()
  const { getCity } = useCitiesIndex()
  const { highlightedRing, isRadialLayerActive, setHighlightedRing } = useRadialHighlight()

  const radialData = ref<RadialHexagon[]>([])
  const isLoadingCells = ref(false)

  function getCellsUrl(cityId: string): string {
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    const base = r2BaseUrl || 'https://data.theurban.world'
    return `${base}/data/city_cells/${cityId}.json`
  }

  async function fetchCityCells(cityId: string): Promise<string[]> {
    const cached = cellsCache.get(cityId)
    if (cached) return cached

    const cells = await $fetch<string[]>(getCellsUrl(cityId))
    cellsCache.set(cityId, cells)
    return cells
  }

  // Build radial data when city or active state changes
  watch(
    [selectedCityId, isRadialLayerActive],
    async ([cityId, active]) => {
      if (!active || !cityId) {
        radialData.value = []
        return
      }

      const city = getCity(cityId)
      if (!city) {
        radialData.value = []
        return
      }

      isLoadingCells.value = true
      try {
        const h3Indices = await fetchCityCells(cityId)
        const [centroidLng, centroidLat] = city.centroid

        radialData.value = h3Indices.map((h3Index) => {
          const [cellLat, cellLng] = cellToLatLng(h3Index)
          const distKm = haversineKm(centroidLat, centroidLng, cellLat, cellLng)
          return { h3Index, ringIndex: Math.floor(distKm) }
        })

        console.log(`[RadialLayer] City ${cityId}: ${radialData.value.length} cells`)
      } catch (e) {
        console.error(`[RadialLayer] Failed to load cells for city ${cityId}:`, e)
        radialData.value = []
      } finally {
        isLoadingCells.value = false
      }
    },
    { immediate: true }
  )

  // Build deck.gl layer
  const layer = computed<Layer | null>(() => {
    if (radialData.value.length === 0) return null

    const highlighted = highlightedRing.value

    return new H3HexagonLayer({
      id: 'radial-ring-layer',
      data: radialData.value,
      getHexagon: (d: RadialHexagon) => d.h3Index,
      getFillColor: (d: RadialHexagon) => {
        if (highlighted != null && d.ringIndex !== highlighted) {
          return getRingColorRGBA(d.ringIndex, 80)
        }
        return getRingColorRGBA(d.ringIndex)
      },
      extruded: false,
      coverage: 1,
      opacity: 0.85,
      stroked: false,
      pickable: true,
      autoHighlight: false,
      onHover: (info) => {
        if (info.object) {
          setHighlightedRing((info.object as RadialHexagon).ringIndex)
        } else {
          setHighlightedRing(null)
        }
      },
      updateTriggers: {
        getFillColor: [highlighted]
      }
    }) as unknown as Layer
  })

  return {
    layer,
    isLoadingCells: readonly(isLoadingCells),
    radialData: readonly(radialData)
  }
}

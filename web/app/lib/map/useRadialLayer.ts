/**
 * Radial density map layer
 *
 * Creates a deck.gl H3HexagonLayer showing a city's H3 cells
 * colored by density intensity. Loads cell indices on-demand
 * per city from R2 (tiny JSON files, ~1-150KB each).
 *
 * Supports both single-city mode (reads from useCitySelection)
 * and comparison mode (accepts explicit cityId + density options).
 */

import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { Layer } from '@deck.gl/core'
import { cellToLatLng } from 'h3-js'
import { getDensityColorRGBA } from '~/utils/densityColors'
import { getRingColorRGBA } from '~/utils/radialColors'

interface RadialHexagon {
  h3Index: string
  ringIndex: number
}

export interface UseRadialLayerOptions {
  /** Override city ID (default: reads from useCitySelection) */
  cityId?: Ref<string | null>
  /** Per-ring density array for density-based coloring */
  densityProfile?: Ref<(number | null)[] | null>
  /** Max density for normalizing the color scale */
  maxDensity?: Ref<number>
  /** Suffix for unique deck.gl layer ID (e.g. 'A', 'B') */
  layerIdSuffix?: string
  /** Always show layer (skip isRadialLayerActive check). Can be a ref for reactive toggling. */
  alwaysActive?: boolean | Ref<boolean>
  /** Disable hover interactions (for comparison maps) */
  disableHover?: boolean
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

export function useRadialLayer(options?: UseRadialLayerOptions) {
  const runtimeConfig = useRuntimeConfig()
  const { selectedCityId } = useCitySelection()
  const { getCity } = useCitiesIndex()
  const { highlightedRing, isRadialLayerActive, setHighlightedRing } = useRadialHighlight()

  // Effective city ID: options override or singleton
  const effectiveCityId = computed(() => options?.cityId?.value ?? selectedCityId.value)

  // Whether this layer should be active
  const isActive = computed(() => unref(options?.alwaysActive) || isRadialLayerActive.value)

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

  // Get epoch-specific centroid if available, otherwise fall back to static centroid
  const { selectedYear } = useSelectedYear()
  const { getCityPopulationData } = useCityPopulations()

  function getCentroidForCity(cityId: string): [number, number] | null {
    // Try epoch-specific H3 centroid first
    const epochData = getCityPopulationData(cityId, selectedYear.value)
    if (epochData?.centroid_h3) {
      const [lat, lng] = cellToLatLng(epochData.centroid_h3)
      return [lat, lng]
    }

    // Fall back to static centroid from cities index
    const city = getCity(cityId)
    if (city?.centroid) {
      // cities index centroid is [lng, lat]
      return [city.centroid[1], city.centroid[0]]
    }

    return null
  }

  // Build radial data when city, active state, or selected year changes
  watch(
    [effectiveCityId, isActive, selectedYear],
    async ([cityId, active]) => {
      if (!active || !cityId) {
        radialData.value = []
        return
      }

      const centroid = getCentroidForCity(cityId)
      if (!centroid) {
        radialData.value = []
        return
      }

      const [centroidLat, centroidLng] = centroid

      isLoadingCells.value = true
      try {
        const h3Indices = await fetchCityCells(cityId)

        radialData.value = h3Indices.map((h3Index) => {
          const [cellLat, cellLng] = cellToLatLng(h3Index)
          const distKm = haversineKm(centroidLat, centroidLng, cellLat, cellLng)
          return { h3Index, ringIndex: Math.floor(distKm) }
        })

        console.log(`[RadialLayer] City ${cityId}: ${radialData.value.length} cells (centroid from ${getCityPopulationData(cityId, selectedYear.value)?.centroid_h3 ? 'H3' : 'index'})`)
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
    const profile = options?.densityProfile?.value
    const maxDen = options?.maxDensity?.value ?? 0
    const useDensityColoring = profile != null && maxDen > 0
    const layerId = 'radial-ring-layer' + (options?.layerIdSuffix ? `-${options.layerIdSuffix}` : '')

    return new H3HexagonLayer({
      id: layerId,
      data: radialData.value,
      getHexagon: (d: RadialHexagon) => d.h3Index,
      getFillColor: (d: RadialHexagon) => {
        if (useDensityColoring) {
          const density = profile[d.ringIndex] ?? 0
          const alpha = (highlighted != null && d.ringIndex !== highlighted) ? 80 : 220
          return getDensityColorRGBA(density, maxDen, false, alpha)
        }
        // Fallback: ring-distance coloring
        if (highlighted != null && d.ringIndex !== highlighted) {
          return getRingColorRGBA(d.ringIndex, 80)
        }
        return getRingColorRGBA(d.ringIndex)
      },
      extruded: false,
      coverage: 1,
      opacity: 0.85,
      stroked: false,
      pickable: !options?.disableHover,
      autoHighlight: false,
      ...(options?.disableHover ? {} : {
        onHover: (info: { object?: unknown }) => {
          if (info.object) {
            setHighlightedRing((info.object as RadialHexagon).ringIndex)
          } else {
            setHighlightedRing(null)
          }
        },
      }),
      updateTriggers: {
        getFillColor: [highlighted, profile, maxDen]
      }
    }) as unknown as Layer
  })

  return {
    layer,
    isLoadingCells: readonly(isLoadingCells),
    radialData: readonly(radialData)
  }
}

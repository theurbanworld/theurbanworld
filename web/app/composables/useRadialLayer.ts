/**
 * Radial density map layer
 *
 * Creates a deck.gl H3HexagonLayer showing a city's H3 cells
 * colored by ring distance from centroid. Supports bidirectional
 * hover sync with the sidebar chart.
 */

import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { Layer } from '@deck.gl/core'
import { cellToLatLng } from 'h3-js'
import type { YearEpoch, H3Hexagon } from '../../types/h3'
import { getRingColorRGBA } from '~/utils/radialColors'

interface RadialHexagon extends H3Hexagon {
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

export function useRadialLayer() {
  const { selectedYear } = useSelectedYear()
  const { selectedCityId } = useCitySelection()
  const { getCity } = useCitiesIndex()
  const { isDataLoaded, loadData: loadH3Data, getDataForCity } = useH3Data()
  const { highlightedRing, isRadialLayerActive, setHighlightedRing } = useRadialHighlight()

  // Computed hexagon data with ring assignments
  const radialData = ref<RadialHexagon[]>([])

  // Load H3 data when radial layer is first activated
  watch(isRadialLayerActive, (active) => {
    if (active && !isDataLoaded.value) {
      loadH3Data().catch(() => {})
    }
  })

  // Recompute when city, year, or layer active state changes
  watch(
    [selectedCityId, selectedYear, isRadialLayerActive, isDataLoaded],
    ([cityId, year, active, loaded]) => {
      if (!active || !cityId || !loaded) {
        radialData.value = []
        return
      }

      const city = getCity(cityId)
      if (!city) {
        radialData.value = []
        return
      }

      const [centroidLng, centroidLat] = city.centroid
      const cells = getDataForCity(cityId, year as YearEpoch)

      console.log(`[RadialLayer] City ${cityId}: ${cells.length} cells for year ${year}`)

      radialData.value = cells.map((cell) => {
        const [cellLat, cellLng] = cellToLatLng(cell.h3Index)
        const distKm = haversineKm(centroidLat, centroidLng, cellLat, cellLng)
        return {
          ...cell,
          ringIndex: Math.floor(distKm),
        }
      })
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
          // Dim non-highlighted rings
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
    radialData: readonly(radialData)
  }
}

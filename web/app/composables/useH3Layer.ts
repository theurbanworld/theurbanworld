/**
 * H3 Population Layer composable
 *
 * Creates and manages a deck.gl H3HexagonLayer for visualizing
 * population density. Uses logarithmic color scale for the sepia gradient.
 */

import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { Layer } from '@deck.gl/core'
import type { H3Hexagon, YearEpoch } from '../../types/h3'
import { getColorForPopulation } from '~/utils/colorScale'

export interface UseH3LayerOptions {
  /** Whether dark mode is enabled */
  isDarkMode?: Ref<boolean> | boolean
}

export function useH3Layer(options: UseH3LayerOptions = {}) {
  const { selectedYear } = useSelectedYear()
  const { isDataLoaded, getDataForYear } = useH3Data()

  // Handle isDarkMode as either ref or boolean
  const isDarkMode = computed(() => {
    const mode = options.isDarkMode
    if (typeof mode === 'boolean') return mode
    if (mode && 'value' in mode) return mode.value
    return false
  })

  // Current H3 data for the selected year
  const hexagonData = ref<H3Hexagon[]>([])

  // Update hexagon data when year changes or data loads
  watch(
    [selectedYear, isDataLoaded],
    ([year, loaded]) => {
      if (loaded) {
        hexagonData.value = getDataForYear(year as YearEpoch)
      }
    },
    { immediate: true }
  )

  /**
   * Create the H3HexagonLayer configuration
   * Returns a new layer instance whenever data or settings change
   */
  const layer = computed<Layer | null>(() => {
    if (hexagonData.value.length === 0) {
      return null
    }

    const darkMode = isDarkMode.value

    return new H3HexagonLayer({
      id: 'h3-population-layer',
      data: hexagonData.value,

      // H3 index accessor
      getHexagon: (d: H3Hexagon) => d.h3Index,

      // Color based on population using logarithmic scale
      getFillColor: (d: H3Hexagon) => getColorForPopulation(d.population, darkMode),

      // 2D flat hexagons (no elevation)
      extruded: false,
      elevationScale: 0,

      // Coverage and appearance
      coverage: 1,
      opacity: 0.8,

      // Stroke for hexagon edges (subtle, matching sepia theme)
      stroked: false,

      // Performance optimizations
      pickable: false, // No hover/click on hexagons per spec
      autoHighlight: false,

      // Update triggers for reactive updates
      updateTriggers: {
        getFillColor: [darkMode]
      }
    }) as unknown as Layer
  })

  /**
   * Get the current layer for passing to deck.gl setLayers
   */
  function getLayer(): Layer | null {
    return layer.value
  }

  /**
   * Get the current hexagon count for the selected year
   */
  function getVisibleHexagonCount(): number {
    return hexagonData.value.length
  }

  return {
    /** The current H3HexagonLayer instance (reactive) */
    layer,
    /** Get the current layer instance */
    getLayer,
    /** Current hexagon data */
    hexagonData: readonly(hexagonData),
    /** Number of visible hexagons */
    getVisibleHexagonCount
  }
}

/**
 * Shared state for population heatmap layer toggle
 *
 * Singleton state controlling the per-city H3 population
 * layer visibility on the map.
 */

const isPopulationLayerActive = ref(false)
const isLoadingH3 = ref(false)

export function usePopulationHighlight() {
  function setPopulationLayerActive(active: boolean) {
    isPopulationLayerActive.value = active
  }

  return {
    isPopulationLayerActive: readonly(isPopulationLayerActive),
    isLoadingH3,
    setPopulationLayerActive
  }
}

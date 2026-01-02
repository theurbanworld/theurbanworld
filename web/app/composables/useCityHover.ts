/**
 * City hover state management
 *
 * Manages the hover state for city boundaries, providing reactive
 * state for MapLibre feature-state boundary highlighting.
 */

// Singleton reactive state - just track the hovered city ID
const hoveredCityId = ref<string | null>(null)
const isHovering = computed(() => hoveredCityId.value !== null)

export function useCityHover() {
  /**
   * Set the hovered city ID
   *
   * @param cityId - City ID from feature properties
   */
  function setHoveredCityId(cityId: string) {
    hoveredCityId.value = cityId
  }

  /**
   * Clear the hover state
   */
  function clearHover() {
    hoveredCityId.value = null
  }

  return {
    /** Currently hovered city ID (readonly) */
    hoveredCityId: readonly(hoveredCityId),
    /** Whether any city is being hovered */
    isHovering,
    /** Set the hovered city ID */
    setHoveredCityId,
    /** Clear hover state */
    clearHover
  }
}

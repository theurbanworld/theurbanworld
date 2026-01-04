/**
 * City selection state management
 *
 * Manages the selected city state, providing reactive
 * state for displaying city info panel and map boundary highlighting.
 *
 * This composable uses the singleton pattern to share state
 * across all components that need to react to city selection.
 */

// Singleton reactive state - track the selected city ID
const selectedCityId = ref<string | null>(null)
const hasSelection = computed(() => selectedCityId.value !== null)

export function useCitySelection() {
  /**
   * Select a city by ID
   *
   * @param cityId - City ID from feature properties or route params
   */
  function selectCity(cityId: string) {
    selectedCityId.value = cityId
  }

  /**
   * Clear the current city selection
   */
  function clearSelection() {
    selectedCityId.value = null
  }

  /**
   * Check if a specific city is selected
   *
   * @param cityId - City ID to check
   * @returns Computed boolean indicating if the city is selected
   */
  function isSelected(cityId: string) {
    return computed(() => selectedCityId.value === cityId)
  }

  return {
    /** Currently selected city ID (readonly) */
    selectedCityId: readonly(selectedCityId),
    /** Whether any city is selected */
    hasSelection,
    /** Select a city by ID */
    selectCity,
    /** Clear the current selection */
    clearSelection,
    /** Check if a specific city is selected */
    isSelected
  }
}

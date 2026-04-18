/**
 * Shared state for comparison radial layer toggle
 *
 * Separate from useRadialHighlight (single-city mode) to avoid conflicts.
 */

const isActive = ref(false)

export function useComparisonRadial() {
  function setActive(active: boolean) {
    isActive.value = active
  }

  return {
    isComparisonRadialActive: readonly(isActive),
    setComparisonRadialActive: setActive
  }
}

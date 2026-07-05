/**
 * Persistent open/close state for the global population panel.
 * Survives navigation — the panel stays collapsed until the user opens it.
 */

const isExpanded = ref(false)

export function useGlobalPopulationPanel() {
  function toggle() {
    isExpanded.value = !isExpanded.value
  }

  return {
    isExpanded: readonly(isExpanded),
    toggle
  }
}

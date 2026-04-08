/**
 * Persistent open/close state for the global population panel.
 * Survives navigation — the panel stays open as the user moves around.
 */

const isExpanded = ref(true)

export function useGlobalPopulationPanel() {
  function toggle() {
    isExpanded.value = !isExpanded.value
  }

  return {
    isExpanded: readonly(isExpanded),
    toggle
  }
}

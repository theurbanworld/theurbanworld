/**
 * Eyebrow panel visibility state
 *
 * Persists the expanded/collapsed state of the eyebrow panel
 * across navigation within the app.
 */

const isExpanded = ref(true)

export function useEyebrowPanel() {
  function toggle() {
    isExpanded.value = !isExpanded.value
  }

  return {
    isExpanded: readonly(isExpanded),
    toggle
  }
}

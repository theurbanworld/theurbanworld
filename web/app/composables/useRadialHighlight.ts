/**
 * Shared state for radial profile bidirectional hover sync
 *
 * Singleton state for highlighting rings in both chart and map layer.
 */

const highlightedRing = ref<number | null>(null)
const isRadialLayerActive = ref(false)

export function useRadialHighlight() {
  function setHighlightedRing(ring: number | null) {
    highlightedRing.value = ring
  }

  function setRadialLayerActive(active: boolean) {
    isRadialLayerActive.value = active
    if (!active) {
      highlightedRing.value = null
    }
  }

  return {
    highlightedRing: readonly(highlightedRing),
    isRadialLayerActive: readonly(isRadialLayerActive),
    setHighlightedRing,
    setRadialLayerActive
  }
}

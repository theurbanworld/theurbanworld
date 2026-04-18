/**
 * Comparison view state management
 *
 * Manages shared zoom level and independent per-map centers for the
 * comparison dual-map layout. When one map zooms, both maps match.
 * When one map pans, only that map moves.
 *
 * Uses a sourceMapId guard to prevent zoom feedback loops when
 * one map's zoom change triggers the other map's update.
 */

// Singleton state for comparison view
const sharedZoom = ref(1.5)
const centerA = ref<{ lng: number, lat: number }>({ lng: 0, lat: 15 })
const centerB = ref<{ lng: number, lat: number }>({ lng: 0, lat: 15 })

// Feedback loop guard: tracks which map last changed the zoom
// to prevent A → zoom → B → zoom → A oscillation
let lastZoomSourceMapId: string | null = null

export function useComparisonViewState() {
  /**
   * Update the shared zoom level from a map interaction.
   * The sourceMapId guard prevents the other map from re-triggering
   * a zoom change when it responds to this update.
   */
  function onZoomChange(zoom: number, sourceMapId: string) {
    lastZoomSourceMapId = sourceMapId
    sharedZoom.value = zoom
  }

  /**
   * Update a map's center from a pan interaction.
   * Only affects the specified map — the other map's center is unchanged.
   */
  function onPanChange(center: { lng: number, lat: number }, mapId: string) {
    if (mapId === 'A') {
      centerA.value = center
    } else {
      centerB.value = center
    }
  }

  /**
   * Check if a zoom change was caused by a specific map.
   * Used by each map to decide whether to respond to a sharedZoom update.
   */
  function isZoomSource(mapId: string): boolean {
    return lastZoomSourceMapId === mapId
  }

  /**
   * Clear the zoom source guard (called after a map finishes its
   * zoom animation via moveend).
   */
  function clearZoomSource() {
    lastZoomSourceMapId = null
  }

  /**
   * Set the initial center for a map (used on mount when fitting to bbox).
   */
  function setCenter(center: { lng: number, lat: number }, mapId: string) {
    if (mapId === 'A') {
      centerA.value = center
    } else {
      centerB.value = center
    }
  }

  /**
   * Get the center ref for a specific map.
   */
  function getCenter(mapId: string) {
    return mapId === 'A' ? centerA : centerB
  }

  /**
   * Reset comparison view state (called when leaving comparison mode).
   */
  function reset() {
    sharedZoom.value = 1.5
    centerA.value = { lng: 0, lat: 15 }
    centerB.value = { lng: 0, lat: 15 }
    lastZoomSourceMapId = null
  }

  return {
    sharedZoom: readonly(sharedZoom),
    centerA: readonly(centerA),
    centerB: readonly(centerB),
    onZoomChange,
    onPanChange,
    isZoomSource,
    clearZoomSource,
    setCenter,
    getCenter,
    reset
  }
}

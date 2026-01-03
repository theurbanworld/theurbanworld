/**
 * Synchronized map view state management
 *
 * Provides a centralized view state store for MapLibre and deck.gl synchronization.
 * Locks pitch and bearing to 0 for 2D-only map viewing (north always up).
 */

/**
 * View state for map positioning
 */
export interface ViewState {
  longitude: number
  latitude: number
  zoom: number
  pitch: number
  bearing: number
}

// Global view state: center [0, 15] at zoom 1.5 to show all continents
const DEFAULT_VIEW_STATE: ViewState = {
  longitude: 0,
  latitude: 15,
  zoom: 1.5,
  pitch: 0,
  bearing: 0
}

// Singleton reactive state shared across composable instances
const viewState = ref<ViewState>({ ...DEFAULT_VIEW_STATE })

export function useViewState() {
  /**
   * Set the view state programmatically
   * Locks pitch to 0 and bearing to 0 in all state updates
   */
  function setViewState(newState: Partial<ViewState>) {
    viewState.value = {
      ...viewState.value,
      ...newState,
      // Always lock pitch and bearing for 2D-only view
      pitch: 0,
      bearing: 0
    }
  }

  /**
   * Update view state from map move events
   * Called when user pans/zooms the map
   */
  function onViewStateChange(newState: ViewState) {
    viewState.value = {
      longitude: newState.longitude,
      latitude: newState.latitude,
      zoom: newState.zoom,
      // Lock pitch and bearing to 0
      pitch: 0,
      bearing: 0
    }
  }

  /**
   * Set zoom level while preserving current position
   * Convenience method for snap-to-level functionality
   *
   * @param zoom - New zoom level to set
   */
  function setZoom(zoom: number) {
    viewState.value = {
      ...viewState.value,
      zoom,
      // Lock pitch and bearing to 0
      pitch: 0,
      bearing: 0
    }
  }

  /**
   * Reset to default global view
   */
  function resetViewState() {
    viewState.value = { ...DEFAULT_VIEW_STATE }
  }

  return {
    viewState: readonly(viewState),
    setViewState,
    setZoom,
    onViewStateChange,
    resetViewState
  }
}

/**
 * Map view state types for MapLibre and deck.gl integration
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

/**
 * Bounding box type for map bounds
 */
export interface MapBounds {
  west: number
  south: number
  east: number
  north: number
}

/**
 * Initial view state configuration
 */
export interface InitialViewConfig {
  center: [number, number] // [longitude, latitude]
  zoom: number
}

/**
 * Map loading state
 */
export interface MapLoadingState {
  isLoading: boolean
  error: Error | null
}

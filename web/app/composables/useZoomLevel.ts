/**
 * Zoom level mapping and utilities
 *
 * Provides zoom level definitions with named scales, icons, and zoom ranges.
 * Used for the vertical zoom slider with snap-to-level functionality.
 */

import { useViewState } from './useViewState'

/**
 * Zoom level name type
 */
export type ZoomLevelName = 'Metropolitan' | 'City' | 'Neighborhood' | 'Street' | 'Building'

/**
 * Zoom level definition
 */
export interface ZoomLevel {
  /** Display name for the zoom level */
  name: ZoomLevelName
  /** Lucide icon class */
  icon: string
  /** Minimum zoom value for this level (inclusive) */
  minZoom: number
  /** Maximum zoom value for this level (exclusive, except for Building) */
  maxZoom: number
  /** Center zoom value for snap-to functionality */
  centerZoom: number
}

/**
 * All zoom levels ordered from low zoom (global view) to high zoom (building view)
 */
const ZOOM_LEVELS: ZoomLevel[] = [
  {
    name: 'Metropolitan',
    icon: 'i-streamline-earth-1-remix',
    minZoom: 0,
    maxZoom: 5,
    centerZoom: 2.5
  },
  {
    name: 'City',
    icon: 'i-lucide-building-2',
    minZoom: 5,
    maxZoom: 10,
    centerZoom: 7.5
  },
  {
    name: 'Neighborhood',
    icon: 'i-lucide-trees',
    minZoom: 10,
    maxZoom: 13,
    centerZoom: 11.5
  },
  {
    name: 'Street',
    icon: 'i-streamline-street-road-remix',
    minZoom: 13,
    maxZoom: 16,
    centerZoom: 14.5
  },
  {
    name: 'Building',
    icon: 'i-lucide-building',
    minZoom: 16,
    maxZoom: 22, // MapLibre max zoom
    centerZoom: 17
  }
]

// Default fallback level (Building)
const DEFAULT_LEVEL: ZoomLevel = ZOOM_LEVELS[ZOOM_LEVELS.length - 1]!

export function useZoomLevel() {
  const { viewState } = useViewState()

  /**
   * Get the zoom level definition for a given zoom value
   *
   * @param zoom - Current zoom value
   * @returns The matching zoom level definition
   */
  function getLevelForZoom(zoom: number): ZoomLevel {
    // Find the level where zoom falls within [minZoom, maxZoom)
    for (const level of ZOOM_LEVELS) {
      if (zoom >= level.minZoom && zoom < level.maxZoom) {
        return level
      }
    }
    // Default to the last level (Building) for very high zooms
    return DEFAULT_LEVEL
  }

  /**
   * Get the center zoom value for a named level
   *
   * @param name - Level name to get center zoom for
   * @returns Center zoom value for snap-to functionality
   */
  function getCenterZoomForLevel(name: ZoomLevelName): number {
    const level = ZOOM_LEVELS.find(l => l.name === name)
    return level?.centerZoom ?? 7.5 // Default to City level
  }

  /**
   * Get a zoom level by name
   *
   * @param name - Level name
   * @returns The zoom level definition or undefined
   */
  function getLevelByName(name: ZoomLevelName): ZoomLevel | undefined {
    return ZOOM_LEVELS.find(l => l.name === name)
  }

  /**
   * Current zoom level based on view state
   */
  const currentLevel = computed(() => {
    return getLevelForZoom(viewState.value.zoom)
  })

  /**
   * Current level name based on view state
   */
  const currentLevelName = computed(() => {
    return currentLevel.value.name
  })

  /**
   * Current level icon based on view state
   */
  const currentLevelIcon = computed(() => {
    return currentLevel.value.icon
  })

  return {
    /** All zoom level definitions */
    ZOOM_LEVELS,
    /** Get level definition for a zoom value */
    getLevelForZoom,
    /** Get center zoom for snap-to-level */
    getCenterZoomForLevel,
    /** Get level by name */
    getLevelByName,
    /** Current zoom level (reactive) */
    currentLevel,
    /** Current level name (reactive) */
    currentLevelName,
    /** Current level icon (reactive) */
    currentLevelIcon
  }
}

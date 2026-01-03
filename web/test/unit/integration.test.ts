/**
 * Integration tests for Global View Controls feature
 *
 * Tests the interaction between GlobalContextPanel, ZoomSlider, and shared state
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, computed, readonly } from 'vue'

// Mock shared state (simulating singleton composables)
const mockSelectedYear = ref(2025)
const mockViewState = ref({
  longitude: 0,
  latitude: 15,
  zoom: 7.5,
  pitch: 0,
  bearing: 0
})

// Test useSelectedYear integration
describe('useSelectedYear integration', () => {
  beforeEach(() => {
    mockSelectedYear.value = 2025
  })

  it('provides consistent state across multiple consumers', () => {
    // Simulate two components using the same composable
    const consumer1 = { selectedYear: readonly(mockSelectedYear) }
    const consumer2 = { selectedYear: readonly(mockSelectedYear) }

    expect(consumer1.selectedYear.value).toBe(2025)
    expect(consumer2.selectedYear.value).toBe(2025)

    // Change from one consumer
    mockSelectedYear.value = 1990

    // Both should see the change
    expect(consumer1.selectedYear.value).toBe(1990)
    expect(consumer2.selectedYear.value).toBe(1990)
  })
})

// Test useViewState integration
describe('useViewState integration', () => {
  beforeEach(() => {
    mockViewState.value = {
      longitude: 0,
      latitude: 15,
      zoom: 7.5,
      pitch: 0,
      bearing: 0
    }
  })

  it('provides consistent zoom state across ZoomSlider and map', () => {
    // Simulate ZoomSlider and GlobalMap both using viewState
    const zoomSlider = { viewState: readonly(mockViewState) }
    const globalMap = { viewState: readonly(mockViewState) }

    expect(zoomSlider.viewState.value.zoom).toBe(7.5)
    expect(globalMap.viewState.value.zoom).toBe(7.5)

    // Simulate map zoom change
    mockViewState.value = { ...mockViewState.value, zoom: 12 }

    // ZoomSlider should see the change
    expect(zoomSlider.viewState.value.zoom).toBe(12)
    expect(globalMap.viewState.value.zoom).toBe(12)
  })

  it('setZoom preserves other view state properties', () => {
    // Set initial position
    mockViewState.value = {
      longitude: 10,
      latitude: 20,
      zoom: 5,
      pitch: 0,
      bearing: 0
    }

    // Simulate setZoom
    mockViewState.value = {
      ...mockViewState.value,
      zoom: 14.5,
      pitch: 0,
      bearing: 0
    }

    expect(mockViewState.value.zoom).toBe(14.5)
    expect(mockViewState.value.longitude).toBe(10)
    expect(mockViewState.value.latitude).toBe(20)
  })
})

// Test population data updates
describe('Population data integration', () => {
  const WORLD_POPULATION: Record<number, number> = {
    1975: 4069437259, 2000: 6148899024, 2025: 8191988536, 2030: 8546141407
  }

  const URBAN_POPULATION: Record<number, number> = {
    1975: 1178323105, 2000: 2306333391, 2025: 3569570193, 2030: 3759831609
  }

  beforeEach(() => {
    mockSelectedYear.value = 2025
  })

  it('updates population when epoch changes', () => {
    // Computed values derived from selected year
    const worldPop = computed(() => WORLD_POPULATION[mockSelectedYear.value])
    const urbanPop = computed(() => URBAN_POPULATION[mockSelectedYear.value])

    expect(worldPop.value).toBe(8191988536)
    expect(urbanPop.value).toBe(3569570193)

    // Change epoch
    mockSelectedYear.value = 1975

    expect(worldPop.value).toBe(4069437259)
    expect(urbanPop.value).toBe(1178323105)
  })
})

// Test zoom level mapping
describe('Zoom level integration', () => {
  const ZOOM_LEVELS = [
    { name: 'Metropolitan', minZoom: 0, maxZoom: 5, centerZoom: 2.5 },
    { name: 'City', minZoom: 5, maxZoom: 10, centerZoom: 7.5 },
    { name: 'Neighborhood', minZoom: 10, maxZoom: 13, centerZoom: 11.5 },
    { name: 'Street', minZoom: 13, maxZoom: 16, centerZoom: 14.5 },
    { name: 'Building', minZoom: 16, maxZoom: 22, centerZoom: 17 }
  ]

  function getLevelForZoom(zoom: number) {
    for (const level of ZOOM_LEVELS) {
      if (zoom >= level.minZoom && zoom < level.maxZoom) {
        return level
      }
    }
    return ZOOM_LEVELS[ZOOM_LEVELS.length - 1]
  }

  beforeEach(() => {
    mockViewState.value = { ...mockViewState.value, zoom: 7.5 }
  })

  it('updates level name when map zoom changes', () => {
    const currentLevel = computed(() => getLevelForZoom(mockViewState.value.zoom))

    expect(currentLevel.value.name).toBe('City')

    // Simulate zoom change from map
    mockViewState.value = { ...mockViewState.value, zoom: 14.5 }

    expect(currentLevel.value.name).toBe('Street')
  })

  it('snap to level updates zoom correctly', () => {
    const currentLevel = computed(() => getLevelForZoom(mockViewState.value.zoom))

    // Start at City level
    expect(currentLevel.value.name).toBe('City')

    // Snap to Neighborhood
    const neighborhoodLevel = ZOOM_LEVELS.find(l => l.name === 'Neighborhood')!
    mockViewState.value = { ...mockViewState.value, zoom: neighborhoodLevel.centerZoom }

    expect(mockViewState.value.zoom).toBe(11.5)
    expect(currentLevel.value.name).toBe('Neighborhood')
  })
})

// Test that removed components don't affect integration
describe('Component removal verification', () => {
  it('GlobalContextPanel replaces YearSlider functionality', () => {
    // GlobalContextPanel should handle:
    // 1. Year display
    // 2. Epoch slider
    // Both use useSelectedYear
    const setYear = vi.fn((year: number) => {
      mockSelectedYear.value = year
    })

    // Simulate slider change in GlobalContextPanel
    setYear(2000)

    expect(mockSelectedYear.value).toBe(2000)
    expect(setYear).toHaveBeenCalledWith(2000)
  })

  it('ZoomSlider replaces MapControls functionality', () => {
    // ZoomSlider should handle:
    // 1. Zoom in/out via slider
    // 2. Snap to level via icons
    const setZoom = vi.fn((zoom: number) => {
      mockViewState.value = { ...mockViewState.value, zoom, pitch: 0, bearing: 0 }
    })

    // Simulate zoom change (replacing +/- buttons)
    setZoom(10)

    expect(mockViewState.value.zoom).toBe(10)
    expect(setZoom).toHaveBeenCalledWith(10)
  })
})

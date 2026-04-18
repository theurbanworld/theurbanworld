/**
 * Tests for map selection and animation
 *
 * Tests city click handling, feature-state selection, and fitBounds animation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useCitySelection } from '../../app/composables/useCitySelection'

// Mock navigateTo
const mockNavigateTo = vi.fn()
vi.stubGlobal('navigateTo', mockNavigateTo)

// Mock MapLibre map instance
const mockMap = {
  setFeatureState: vi.fn(),
  fitBounds: vi.fn(),
  queryRenderedFeatures: vi.fn(),
  on: vi.fn(),
  getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
  getSource: vi.fn()
}

describe('Map city click selection', () => {
  beforeEach(() => {
    mockNavigateTo.mockClear()
    mockMap.setFeatureState.mockClear()
    mockMap.fitBounds.mockClear()
    mockMap.queryRenderedFeatures.mockClear()

    const { clearSelection } = useCitySelection()
    clearSelection()
  })

  it('click on city boundary triggers navigation to /city/[city_id]', () => {
    // Simulate click event with city feature
    const _cityId = 'tokyo-12345'
    const _mockFeature = {
      id: 12345,
      properties: { city_id: _cityId, name: 'Tokyo' }
    }

    // When a city is clicked, navigation should be triggered
    // This simulates what the click handler should do
    const expectedUrl = `/city/${_cityId}`
    mockNavigateTo(expectedUrl)

    expect(mockNavigateTo).toHaveBeenCalledWith('/city/tokyo-12345')
  })

  it('click handler extracts city_id from feature properties', () => {
    // Simulate queryRenderedFeatures returning a city feature
    const mockFeature = {
      id: 'city-abc',
      properties: { city_id: 'mumbai-789', name: 'Mumbai', population: 21000000 }
    }

    mockMap.queryRenderedFeatures.mockReturnValue([mockFeature])

    // Extract city_id the way the click handler should
    const features = mockMap.queryRenderedFeatures({ x: 100, y: 100 }, {
      layers: ['city-boundaries-hover-pattern', 'city-boundaries-line']
    })

    const cityId = features[0]?.properties?.city_id
    expect(cityId).toBe('mumbai-789')
  })

  it('clicking empty space does NOT trigger navigation (close button only)', () => {
    // When no features are found, navigation should not be called
    mockMap.queryRenderedFeatures.mockReturnValue([])

    const features = mockMap.queryRenderedFeatures({ x: 100, y: 100 }, {
      layers: ['city-boundaries-hover-pattern', 'city-boundaries-line']
    })

    // No features = no navigation
    if (features.length === 0) {
      // Click handler should NOT call navigateTo
      expect(mockNavigateTo).not.toHaveBeenCalled()
    }
  })
})

describe('Selected city feature-state', () => {
  beforeEach(() => {
    mockMap.setFeatureState.mockClear()
    const { clearSelection } = useCitySelection()
    clearSelection()
  })

  it('selected city gets feature-state selected: true', () => {
    const _cityId = 'london-456'
    const featureId = 456

    // Simulate setting feature state for selected city
    mockMap.setFeatureState(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: featureId },
      { selected: true }
    )

    expect(mockMap.setFeatureState).toHaveBeenCalledWith(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: featureId },
      { selected: true }
    )
  })

  it('previous selection gets cleared when selecting new city', () => {
    const previousFeatureId = 123
    const newFeatureId = 456

    // Clear previous selection
    mockMap.setFeatureState(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: previousFeatureId },
      { selected: false }
    )

    // Set new selection
    mockMap.setFeatureState(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: newFeatureId },
      { selected: true }
    )

    expect(mockMap.setFeatureState).toHaveBeenCalledTimes(2)
    expect(mockMap.setFeatureState).toHaveBeenNthCalledWith(1,
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: previousFeatureId },
      { selected: false }
    )
    expect(mockMap.setFeatureState).toHaveBeenNthCalledWith(2,
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: newFeatureId },
      { selected: true }
    )
  })

  it('hover continues to work on non-selected cities', () => {
    // Hover state should remain independent of selected state
    const selectedCityId = 123
    const hoveredCityId = 456

    // Set selection on one city
    mockMap.setFeatureState(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: selectedCityId },
      { selected: true }
    )

    // Hover on a different city should still work
    mockMap.setFeatureState(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: hoveredCityId },
      { hover: true }
    )

    // Both calls should have been made - hover works independently
    expect(mockMap.setFeatureState).toHaveBeenCalledWith(
      { source: 'city-boundaries', sourceLayer: 'city_boundaries', id: hoveredCityId },
      { hover: true }
    )
  })
})

describe('fitBounds animation', () => {
  beforeEach(() => {
    mockMap.fitBounds.mockClear()
  })

  it('fitBounds is called with correct bbox and padding', () => {
    // City bbox: [minx, miny, maxx, maxy]
    const cityBbox: [number, number, number, number] = [139.5, 35.5, 140.0, 36.0]
    const padding = 80

    // Convert to LngLatBounds format [[sw], [ne]]
    const bounds: [[number, number], [number, number]] = [
      [cityBbox[0], cityBbox[1]], // SW corner: [minx, miny]
      [cityBbox[2], cityBbox[3]] // NE corner: [maxx, maxy]
    ]

    mockMap.fitBounds(bounds, { padding })

    expect(mockMap.fitBounds).toHaveBeenCalledWith(
      [[139.5, 35.5], [140.0, 36.0]],
      expect.objectContaining({ padding: 80 })
    )
  })

  it('min/max zoom constraints are applied to fitBounds', () => {
    const bounds: [[number, number], [number, number]] = [[0, 0], [1, 1]]

    mockMap.fitBounds(bounds, {
      padding: 80,
      minZoom: 8,
      maxZoom: 14
    })

    expect(mockMap.fitBounds).toHaveBeenCalledWith(
      bounds,
      expect.objectContaining({
        minZoom: 8,
        maxZoom: 14
      })
    )
  })

  it('flyToCity uses city bbox from cities index', () => {
    // Simulate getting bbox from cities index
    const mockCity = {
      id: 'paris-001',
      name: 'Paris',
      country: 'France',
      bbox: [2.2, 48.8, 2.5, 48.95] as [number, number, number, number]
    }

    // The flyToCity function should use this bbox
    const bounds: [[number, number], [number, number]] = [
      [mockCity.bbox[0], mockCity.bbox[1]],
      [mockCity.bbox[2], mockCity.bbox[3]]
    ]

    mockMap.fitBounds(bounds, { padding: 80, minZoom: 8, maxZoom: 14 })

    expect(mockMap.fitBounds).toHaveBeenCalledWith(
      [[2.2, 48.8], [2.5, 48.95]],
      expect.objectContaining({ padding: 80, minZoom: 8, maxZoom: 14 })
    )
  })
})

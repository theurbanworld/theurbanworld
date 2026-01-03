/**
 * Tests for global view control composables
 *
 * Tests useGlobalStats, useZoomLevel, and useViewState.setZoom
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useGlobalStats, humanizeNumber } from '../../app/composables/useGlobalStats'
import { useSelectedYear } from '../../app/composables/useSelectedYear'
import { useZoomLevel } from '../../app/composables/useZoomLevel'
import { useViewState } from '../../app/composables/useViewState'

describe('useGlobalStats', () => {
  beforeEach(() => {
    // Reset year to default before each test
    const { setYear } = useSelectedYear()
    setYear(2025)
  })

  it('returns correct world population for a given epoch', () => {
    const { setYear } = useSelectedYear()
    setYear(2025)

    const { worldPopulation, worldPopulationRaw } = useGlobalStats()

    expect(worldPopulationRaw.value).toBe(8191988536)
    expect(worldPopulation.value).toBe('8.2 billion')
  })

  it('returns correct urban population for a given epoch', () => {
    const { setYear } = useSelectedYear()
    setYear(2025)

    const { urbanPopulation, urbanPopulationRaw } = useGlobalStats()

    expect(urbanPopulationRaw.value).toBe(3569570193)
    expect(urbanPopulation.value).toBe('3.6 billion')
  })

  it('updates population values when epoch changes', () => {
    const { setYear } = useSelectedYear()

    // Start at 1975
    setYear(1975)

    const { worldPopulationRaw, urbanPopulationRaw } = useGlobalStats()

    expect(worldPopulationRaw.value).toBe(4069437259)
    expect(urbanPopulationRaw.value).toBe(1178323105)

    // Change to 2030
    setYear(2030)

    expect(worldPopulationRaw.value).toBe(8546141407)
    expect(urbanPopulationRaw.value).toBe(3759831609)
  })

  it('humanizes numbers correctly', () => {
    expect(humanizeNumber(8191988536)).toBe('8.2 billion')
    expect(humanizeNumber(3569570193)).toBe('3.6 billion')
    expect(humanizeNumber(4069437259)).toBe('4.1 billion')
    expect(humanizeNumber(500000000)).toBe('500 million')
    expect(humanizeNumber(1500000)).toBe('1.5 million')
  })
})

describe('useZoomLevel', () => {
  it('maps zoom values to correct named levels', () => {
    const { getLevelForZoom } = useZoomLevel()

    // Test each zoom range
    expect(getLevelForZoom(2).name).toBe('Metropolitan')
    expect(getLevelForZoom(7).name).toBe('City')
    expect(getLevelForZoom(11).name).toBe('Neighborhood')
    expect(getLevelForZoom(14).name).toBe('Street')
    expect(getLevelForZoom(17).name).toBe('Building')

    // Test boundary cases
    expect(getLevelForZoom(0).name).toBe('Metropolitan')
    expect(getLevelForZoom(5).name).toBe('City') // At boundary, goes to next level
    expect(getLevelForZoom(10).name).toBe('Neighborhood')
    expect(getLevelForZoom(13).name).toBe('Street')
    expect(getLevelForZoom(16).name).toBe('Building')
  })

  it('returns correct center zoom for snap-to-level functionality', () => {
    const { getCenterZoomForLevel, ZOOM_LEVELS } = useZoomLevel()

    expect(getCenterZoomForLevel('Metropolitan')).toBe(2.5)
    expect(getCenterZoomForLevel('City')).toBe(7.5)
    expect(getCenterZoomForLevel('Neighborhood')).toBe(11.5)
    expect(getCenterZoomForLevel('Street')).toBe(14.5)
    expect(getCenterZoomForLevel('Building')).toBe(17)

    // Verify all levels have defined centers
    for (const level of ZOOM_LEVELS) {
      expect(getCenterZoomForLevel(level.name)).toBe(level.centerZoom)
    }
  })

  it('provides all level definitions with correct icons', () => {
    const { ZOOM_LEVELS } = useZoomLevel()

    expect(ZOOM_LEVELS).toHaveLength(5)

    // Verify level order (Metropolitan to Building, low to high zoom)
    const metropolitan = ZOOM_LEVELS[0]
    const city = ZOOM_LEVELS[1]
    const neighborhood = ZOOM_LEVELS[2]
    const street = ZOOM_LEVELS[3]
    const building = ZOOM_LEVELS[4]

    expect(metropolitan?.name).toBe('Metropolitan')
    expect(metropolitan?.icon).toBe('i-lucide-globe')

    expect(city?.name).toBe('City')
    expect(city?.icon).toBe('i-lucide-building-2')

    expect(neighborhood?.name).toBe('Neighborhood')
    expect(neighborhood?.icon).toBe('i-lucide-trees')

    expect(street?.name).toBe('Street')
    expect(street?.icon).toBe('i-lucide-road')

    expect(building?.name).toBe('Building')
    expect(building?.icon).toBe('i-lucide-building')
  })
})

describe('useViewState.setZoom', () => {
  beforeEach(() => {
    // Reset view state before each test
    const { resetViewState } = useViewState()
    resetViewState()
  })

  it('updates zoom while preserving other view state properties', () => {
    const { viewState, setViewState, setZoom } = useViewState()

    // Set initial state
    setViewState({
      longitude: 10,
      latitude: 20,
      zoom: 5
    })

    expect(viewState.value.longitude).toBe(10)
    expect(viewState.value.latitude).toBe(20)
    expect(viewState.value.zoom).toBe(5)

    // Use setZoom convenience method
    setZoom(12)

    // Zoom should change, but position should remain
    expect(viewState.value.zoom).toBe(12)
    expect(viewState.value.longitude).toBe(10)
    expect(viewState.value.latitude).toBe(20)
    expect(viewState.value.pitch).toBe(0)
    expect(viewState.value.bearing).toBe(0)
  })
})

/**
 * Tests for global view control composables
 *
 * Tests useGlobalStats, useZoomLevel, and useViewState.setZoom
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useGlobalStats, humanizeNumber, getTrendInfo, calculatePercentage } from '../../app/composables/useGlobalStats'
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

  it('calculates urban population trend from previous epoch', () => {
    const { setYear } = useSelectedYear()
    setYear(2025)

    const { urbanPopulationTrendPrevious } = useGlobalStats()

    // 2020->2025: (3569570193 - 3350187245) / 3350187245 * 100 ≈ 6.55%
    expect(urbanPopulationTrendPrevious.value).toBeCloseTo(6.55, 1)
  })

  it('returns null for trendPrevious at first epoch (1975)', () => {
    const { setYear } = useSelectedYear()
    setYear(1975)

    const { urbanPopulationTrendPrevious } = useGlobalStats()
    expect(urbanPopulationTrendPrevious.value).toBeNull()
  })

  it('returns null for trendNext at last epoch (2030)', () => {
    const { setYear } = useSelectedYear()
    setYear(2030)

    const { urbanPopulationTrendNext } = useGlobalStats()
    expect(urbanPopulationTrendNext.value).toBeNull()
  })

  it('calculates urban percentage of world population', () => {
    const { setYear } = useSelectedYear()
    setYear(2025)

    const { urbanPercentageOfWorld } = useGlobalStats()

    // 3569570193 / 8191988536 * 100 ≈ 43.6%
    expect(urbanPercentageOfWorld.value).toBeCloseTo(43.6, 1)
  })
})

describe('getTrendInfo', () => {
  it('returns strong-up for >= 10% change', () => {
    expect(getTrendInfo(10).level).toBe('strong-up')
    expect(getTrendInfo(15).level).toBe('strong-up')
    expect(getTrendInfo(10).icon).toBe('i-lucide-chevrons-up')
  })

  it('returns moderate-up for 5% to <10% change', () => {
    expect(getTrendInfo(5).level).toBe('moderate-up')
    expect(getTrendInfo(9.9).level).toBe('moderate-up')
    expect(getTrendInfo(7).icon).toBe('i-lucide-chevron-up')
  })

  it('returns stable for -2% to <5% change', () => {
    expect(getTrendInfo(0).level).toBe('stable')
    expect(getTrendInfo(4.9).level).toBe('stable')
    expect(getTrendInfo(-1.9).level).toBe('stable')
    expect(getTrendInfo(2).icon).toBe('i-lucide-minus')
  })

  it('returns moderate-down for -5% to <=-2% change', () => {
    expect(getTrendInfo(-2).level).toBe('moderate-down')
    expect(getTrendInfo(-4.9).level).toBe('moderate-down')
    expect(getTrendInfo(-3).icon).toBe('i-lucide-chevron-down')
  })

  it('returns strong-down for <= -5% change', () => {
    expect(getTrendInfo(-5).level).toBe('strong-down')
    expect(getTrendInfo(-10).level).toBe('strong-down')
    expect(getTrendInfo(-5).icon).toBe('i-lucide-chevrons-down')
  })
})

describe('calculatePercentage', () => {
  it('calculates percentage correctly', () => {
    expect(calculatePercentage(50, 100)).toBe(50)
    expect(calculatePercentage(1, 3)).toBeCloseTo(33.3, 1)
  })

  it('returns 0 when whole is 0', () => {
    expect(calculatePercentage(50, 0)).toBe(0)
  })

  it('handles large numbers', () => {
    expect(calculatePercentage(3569570193, 8191988536)).toBeCloseTo(43.6, 1)
  })
})

describe('useZoomLevel', () => {
  it('maps zoom values to correct named levels', () => {
    const { getLevelForZoom } = useZoomLevel()

    // Test each zoom range
    expect(getLevelForZoom(2).name).toBe('Globe')
    expect(getLevelForZoom(4.5).name).toBe('Country')
    expect(getLevelForZoom(7).name).toBe('Region')
    expect(getLevelForZoom(12).name).toBe('City')
    expect(getLevelForZoom(15).name).toBe('Street')

    // Test boundary cases
    expect(getLevelForZoom(0).name).toBe('Globe')
    expect(getLevelForZoom(3).name).toBe('Country') // At boundary, goes to next level
    expect(getLevelForZoom(6.5).name).toBe('Region')
    expect(getLevelForZoom(10.5).name).toBe('City')
    expect(getLevelForZoom(14.5).name).toBe('Street')
  })

  it('returns correct center zoom for snap-to-level functionality', () => {
    const { getCenterZoomForLevel, ZOOM_LEVELS } = useZoomLevel()

    expect(getCenterZoomForLevel('Globe')).toBe(1.5)
    expect(getCenterZoomForLevel('Country')).toBe(4.5)
    expect(getCenterZoomForLevel('Region')).toBe(8)
    expect(getCenterZoomForLevel('City')).toBe(13)
    expect(getCenterZoomForLevel('Street')).toBe(16)

    // Verify all levels have defined centers
    for (const level of ZOOM_LEVELS) {
      expect(getCenterZoomForLevel(level.name)).toBe(level.centerZoom)
    }
  })

  it('provides all level definitions with correct icons', () => {
    const { ZOOM_LEVELS } = useZoomLevel()

    expect(ZOOM_LEVELS).toHaveLength(5)

    // Verify level order (Globe to Street, low to high zoom)
    const globe = ZOOM_LEVELS[0]
    const country = ZOOM_LEVELS[1]
    const region = ZOOM_LEVELS[2]
    const city = ZOOM_LEVELS[3]
    const street = ZOOM_LEVELS[4]

    expect(globe?.name).toBe('Globe')
    expect(globe?.icon).toBe('i-streamline-earth-1-remix')

    expect(country?.name).toBe('Country')
    expect(country?.icon).toBe('i-lucide-flag')

    expect(region?.name).toBe('Region')
    expect(region?.icon).toBe('i-lucide-train-front')

    expect(city?.name).toBe('City')
    expect(city?.icon).toBe('i-lucide-trees')

    expect(street?.name).toBe('Street')
    expect(street?.icon).toBe('i-streamline-street-road-remix')
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

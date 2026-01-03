/**
 * Tests for global view control composables
 *
 * Tests useGlobalStats, useZoomLevel, and useViewState.setZoom
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useGlobalStats, humanizeNumber, getTrendInfo, calculatePercentage, toAnnualRate } from '../../app/composables/useGlobalStats'
import { useSelectedYear } from '../../app/composables/useSelectedYear'
import { useZoomLevel } from '../../app/composables/useZoomLevel'
import { useViewState } from '../../app/composables/useViewState'
import { useDataPointHighlight } from '../../app/composables/useDataPointHighlight'

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

  it('calculates annualized urban population trend from previous epoch', () => {
    const { setYear } = useSelectedYear()
    setYear(2025)

    const { urbanPopulationTrendPrevious } = useGlobalStats()

    // 2020->2025: 5-year rate ~6.55% → annualized ~1.28%
    expect(urbanPopulationTrendPrevious.value).toBeCloseTo(1.28, 1)
  })

  it('calculates annualized world population trend from previous epoch', () => {
    const { setYear } = useSelectedYear()
    setYear(2025)

    const { worldPopulationTrendPrevious } = useGlobalStats()

    // 2020->2025: 5-year rate ~4.48% → annualized ~0.88%
    expect(worldPopulationTrendPrevious.value).toBeCloseTo(0.88, 1)
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
  it('returns strong-up with -40° rotation and emerald color for >= 2% change', () => {
    expect(getTrendInfo(2).level).toBe('strong-up')
    expect(getTrendInfo(3).level).toBe('strong-up')
    expect(getTrendInfo(2).icon).toBe('i-lucide-move-right')
    expect(getTrendInfo(2).rotation).toBe(-40)
    expect(getTrendInfo(2).colorClass).toContain('emerald')
  })

  it('returns moderate-up with -20° rotation and green color for 1% to <2% change', () => {
    expect(getTrendInfo(1).level).toBe('moderate-up')
    expect(getTrendInfo(1.9).level).toBe('moderate-up')
    expect(getTrendInfo(1.5).icon).toBe('i-lucide-move-right')
    expect(getTrendInfo(1.5).rotation).toBe(-20)
    expect(getTrendInfo(1.5).colorClass).toContain('green')
  })

  it('returns stable with 0° rotation and gray color for -0.4% to <1% change', () => {
    expect(getTrendInfo(0).level).toBe('stable')
    expect(getTrendInfo(0.9).level).toBe('stable')
    expect(getTrendInfo(-0.3).level).toBe('stable')
    expect(getTrendInfo(0.5).icon).toBe('i-lucide-move-right')
    expect(getTrendInfo(0.5).rotation).toBe(0)
    expect(getTrendInfo(0.5).colorClass).toContain('gray')
  })

  it('returns moderate-down with +20° rotation and amber color for -1% to <=-0.4% change', () => {
    expect(getTrendInfo(-0.4).level).toBe('moderate-down')
    expect(getTrendInfo(-0.9).level).toBe('moderate-down')
    expect(getTrendInfo(-0.6).icon).toBe('i-lucide-move-right')
    expect(getTrendInfo(-0.6).rotation).toBe(20)
    expect(getTrendInfo(-0.6).colorClass).toContain('amber')
  })

  it('returns strong-down with +40° rotation and red color for <= -1% change', () => {
    expect(getTrendInfo(-1).level).toBe('strong-down')
    expect(getTrendInfo(-2).level).toBe('strong-down')
    expect(getTrendInfo(-1).icon).toBe('i-lucide-move-right')
    expect(getTrendInfo(-1).rotation).toBe(40)
    expect(getTrendInfo(-1).colorClass).toContain('red')
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

describe('toAnnualRate', () => {
  it('converts 5-year rate to annualized rate', () => {
    // 6.55% over 5 years → ~1.28% per year
    expect(toAnnualRate(6.55)).toBeCloseTo(1.28, 1)
  })

  it('handles zero rate', () => {
    expect(toAnnualRate(0)).toBe(0)
  })

  it('handles negative rates', () => {
    // -5% over 5 years → ~-1.02% per year
    expect(toAnnualRate(-5)).toBeCloseTo(-1.02, 1)
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

describe('useDataPointHighlight', () => {
  beforeEach(() => {
    // Clear highlight state before each test
    const { setHighlight } = useDataPointHighlight()
    setHighlight(null)
  })

  it('starts with null highlighted ID', () => {
    const { highlightedId } = useDataPointHighlight()
    expect(highlightedId.value).toBeNull()
  })

  it('setHighlight updates the highlighted ID', () => {
    const { highlightedId, setHighlight } = useDataPointHighlight()

    setHighlight('world-population')
    expect(highlightedId.value).toBe('world-population')

    setHighlight('urban-population')
    expect(highlightedId.value).toBe('urban-population')

    setHighlight(null)
    expect(highlightedId.value).toBeNull()
  })

  it('isHighlighted returns correct boolean for given ID', () => {
    const { setHighlight, isHighlighted } = useDataPointHighlight()

    setHighlight('world-population')

    expect(isHighlighted('world-population').value).toBe(true)
    expect(isHighlighted('urban-population').value).toBe(false)
    expect(isHighlighted('other-id').value).toBe(false)
  })

  it('state is shared across multiple calls to useDataPointHighlight', () => {
    const instance1 = useDataPointHighlight()
    const instance2 = useDataPointHighlight()

    instance1.setHighlight('test-id')

    expect(instance2.highlightedId.value).toBe('test-id')
    expect(instance2.isHighlighted('test-id').value).toBe(true)
  })
})

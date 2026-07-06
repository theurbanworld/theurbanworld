/**
 * Tests for climate support in useDistributionData (plan U9)
 *
 * A climate headline metric ranks over the climate-city SUBSET, not all cities,
 * so the headline DistributionStrip and rankings compute "N of M" correctly.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useCityClimate } from '../../app/composables/useCityClimate'
import { useDistributionData } from '../../app/composables/useDistributionData'
import { SOLAR_HEADLINE_KEY } from '../../types/climate'

const summary = {
  A: { [SOLAR_HEADLINE_KEY]: 1500 },
  B: { [SOLAR_HEADLINE_KEY]: 1320 },
  C: { [SOLAR_HEADLINE_KEY]: 1800 }
}

describe('useDistributionData (climate)', () => {
  beforeEach(() => {
    clearNuxtData('climate-summary')
    clearNuxtData('climate-profile')
    vi.unstubAllGlobals()
  })

  it('ranks a climate metric over the climate subset only', async () => {
    vi.stubGlobal('$fetch', vi.fn(() => Promise.resolve(summary)))
    await useCityClimate().loadSummary()

    const { sortedDistribution, rankLabel } = useDistributionData(
      ref('B'),
      ref(SOLAR_HEADLINE_KEY)
    )

    // Only the 3 covered cities, sorted ascending by value
    expect(sortedDistribution.value.map(e => e.cityId)).toEqual(['B', 'A', 'C'])
    // B has the smallest solar -> ranks last of 3 (largest = #1); M = climate subset size
    expect(rankLabel.value).toBe('#3 of 3')
  })

  it('returns empty distribution before the summary loads', () => {
    vi.stubGlobal('$fetch', vi.fn(() => Promise.resolve(summary)))
    const { sortedDistribution } = useDistributionData(ref('A'), ref(SOLAR_HEADLINE_KEY))
    expect(sortedDistribution.value).toEqual([])
  })
})

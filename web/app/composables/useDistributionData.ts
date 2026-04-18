/**
 * City distribution data for ranking visualizations
 *
 * Sorts all cities by a given metric at the current epoch to produce
 * a distribution curve. Provides rank, percentile, and tooltip lookups.
 */

import type { YearEpoch } from '../../types/h3'

export type DistributionMetric = 'population' | 'density_per_km2' | 'area_km2'

export interface DistributionEntry {
  cityId: string
  value: number
}

export function useDistributionData(
  cityId: MaybeRef<string>,
  metric: MaybeRef<DistributionMetric>
) {
  const { populationsMap } = useCityPopulations()
  const { selectedYear } = useSelectedYear()
  const { getCityName } = useCitiesIndex()

  // Sorted distribution of all cities for this metric at the current epoch
  const sortedDistribution = computed((): DistributionEntry[] => {
    const map = populationsMap.value
    if (!map) return []

    const epoch = selectedYear.value as YearEpoch
    const m = toValue(metric)
    const entries: DistributionEntry[] = []

    for (const [id, epochs] of map) {
      const val = epochs[epoch]?.[m]
      if (val != null && val > 0) {
        entries.push({ cityId: id, value: val })
      }
    }

    entries.sort((a, b) => a.value - b.value)
    return entries
  })

  // Current city's rank (0-based index in sorted array)
  const cityRank = computed(() => {
    const id = toValue(cityId)
    return sortedDistribution.value.findIndex(e => e.cityId === id)
  })

  // Percentile (0-100), where 97 means "larger than 97% of cities"
  const cityPercentile = computed(() => {
    const sorted = sortedDistribution.value
    const rank = cityRank.value
    if (sorted.length === 0 || rank < 0) return 0
    return (rank / (sorted.length - 1)) * 100
  })

  // Ordinal rank label: "Rank 342 of 11,204"
  const rankLabel = computed(() => {
    const sorted = sortedDistribution.value
    const rank = cityRank.value
    if (sorted.length === 0 || rank < 0) return ''
    // Display as 1-based, largest = rank 1
    const displayRank = sorted.length - rank
    return `#${displayRank.toLocaleString()} of ${sorted.length.toLocaleString()}`
  })

  /**
   * Get city info at a given index in the sorted distribution.
   * Used by tooltip callbacks.
   */
  function getCityAtIndex(index: number): { name: string, value: number } | null {
    const sorted = sortedDistribution.value
    const clamped = Math.max(0, Math.min(index, sorted.length - 1))
    const entry = sorted[clamped]
    if (!entry) return null
    return {
      name: getCityName(entry.cityId) ?? entry.cityId,
      value: entry.value
    }
  }

  return {
    sortedDistribution,
    cityRank,
    cityPercentile,
    rankLabel,
    getCityAtIndex
  }
}

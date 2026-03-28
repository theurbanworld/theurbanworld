<script setup lang="ts">
/**
 * RankingFilters - Stat toggle and country filter for rankings
 *
 * Rendered in the sidebar header (non-scrollable section).
 * Shares state with CityRankings via useRankingFilters composable.
 */

import type { YearEpoch } from '../../../types/h3'
import type { RankingStat } from '~/composables/useRankingFilters'

const { activeStat, countryFilter, sortDirection } = useRankingFilters()
const { selectedYear } = useSelectedYear()
const { allCities } = useCitiesIndex()
const { getCityPopulationData } = useCityPopulations()

const stats: { key: RankingStat; label: string }[] = [
  { key: 'population', label: 'Population' },
  { key: 'density', label: 'Density' },
  { key: 'area', label: 'Area' },
  { key: 'growth', label: 'Growth' }
]

// Unique countries sorted
const countries = computed(() => {
  const set = new Set(allCities.value.map(c => c.country))
  return [...set].sort()
})

// City count (respects country filter)
const cityCount = computed(() => {
  let count = 0
  for (const city of allCities.value) {
    const popData = getCityPopulationData(city.id, selectedYear.value as YearEpoch)
    if (!popData) continue
    if (countryFilter.value && city.country !== countryFilter.value) continue
    count++
  }
  return count
})
</script>

<template>
  <div class="px-4 py-3 border-b border-ink-200/40 dark:border-ink-800/40">
    <!-- Stat toggle -->
    <div class="flex gap-1 mb-3">
      <button
        v-for="stat in stats"
        :key="stat.key"
        class="flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer"
        :class="activeStat === stat.key
          ? 'bg-ink-700 text-white dark:bg-ink-400 dark:text-ink-950'
          : 'text-body/70 dark:text-cream/70 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
        @click="activeStat = stat.key"
      >
        {{ stat.label }}
      </button>
    </div>

    <!-- Country filter -->
    <select
      v-model="countryFilter"
      class="w-full text-sm rounded-md
             bg-parchment text-body dark:text-cream/90
             border border-ink-200/40 dark:border-ink-800/40
             px-2 py-1.5 cursor-pointer
             focus:outline-none focus:ring-2 focus:ring-ink-300/50 dark:focus:ring-ink-700/50"
    >
      <option value="">
        All countries
      </option>
      <option v-for="c in countries" :key="c" :value="c">
        {{ c }}
      </option>
    </select>

    <!-- Count + sort toggle -->
    <div class="flex items-center justify-between mt-2">
      <p class="text-xs text-body/50 dark:text-cream/50">
        {{ cityCount.toLocaleString() }} cities<span v-if="countryFilter"> in {{ countryFilter }}</span>
      </p>
      <button
        class="flex items-center gap-1 text-xs text-body/50 dark:text-cream/50
               hover:text-ink-700 dark:hover:text-ink-300 transition-colors cursor-pointer"
        @click="sortDirection = sortDirection === 'desc' ? 'asc' : 'desc'"
      >
        <UIcon
          :name="sortDirection === 'desc' ? 'i-lucide-arrow-down-wide-narrow' : 'i-lucide-arrow-up-wide-narrow'"
          class="w-3.5 h-3.5"
        />
        {{ sortDirection === 'desc' ? 'Highest' : 'Lowest' }}
      </button>
    </div>
  </div>
</template>

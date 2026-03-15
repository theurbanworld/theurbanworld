<script setup lang="ts">
/**
 * CityRankings - Scrollable ranked city list with horizontal bar visualization
 *
 * Filter controls live in the sidebar header (via RankingFilters).
 * This component renders only the scrollable list.
 */

import type { YearEpoch } from '../../../types/h3'
import { formatCompactNumber, formatDensity, formatArea } from '~/utils/formatNumber'

const { activeStat, countryFilter } = useRankingFilters()
const { selectedYear } = useSelectedYear()
const { allCities } = useCitiesIndex()
const { getCityPopulationData } = useCityPopulations()

const displayCount = ref(100)

interface RankedCity {
  id: string
  name: string
  country: string
  population: number
  density: number
  area: number
}

const rankedCities = computed<RankedCity[]>(() => {
  const cities: RankedCity[] = []

  for (const city of allCities.value) {
    const popData = getCityPopulationData(city.id, selectedYear.value as YearEpoch)
    if (!popData) continue
    if (countryFilter.value && city.country !== countryFilter.value) continue
    cities.push({
      id: city.id,
      name: city.name,
      country: city.country,
      population: popData.population,
      density: popData.density_per_km2,
      area: popData.area_km2
    })
  }

  cities.sort((a, b) => b[activeStat.value] - a[activeStat.value])

  return cities
})

const maxValue = computed(() => {
  if (!rankedCities.value.length) return 1
  return rankedCities.value[0]![activeStat.value]
})

const displayedCities = computed(() =>
  rankedCities.value.slice(0, displayCount.value)
)

const hasMore = computed(() =>
  rankedCities.value.length > displayCount.value
)

function formatValue(city: RankedCity): string {
  switch (activeStat.value) {
    case 'density': return formatDensity(city.density)
    case 'area': return formatArea(city.area)
    default: return formatCompactNumber(city.population)
  }
}

function barPercent(city: RankedCity): string {
  return `${(city[activeStat.value] / maxValue.value) * 100}%`
}

function showMore() {
  displayCount.value += 100
}

function selectCity(id: string) {
  navigateTo(`/city/${id}`)
}

// Reset display count when filter or stat changes
watch([activeStat, countryFilter], () => {
  displayCount.value = 100
})
</script>

<template>
  <div>
    <button
      v-for="(city, index) in displayedCities"
      :key="city.id"
      class="w-full text-left relative py-2 px-5
             hover:bg-forest-100/30 dark:hover:bg-forest-900/20
             transition-colors cursor-pointer"
      @click="selectCity(city.id)"
    >
      <!-- Bar background -->
      <div
        class="absolute inset-y-0 left-0 bg-forest-100/60 dark:bg-forest-800/30"
        :style="{ width: barPercent(city) }"
      />
      <!-- Content -->
      <div class="relative flex items-baseline gap-2">
        <span class="text-xs text-body/40 dark:text-cream/40 w-6 text-right shrink-0 tabular-nums">
          {{ index + 1 }}
        </span>
        <span class="text-sm font-medium text-espresso dark:text-dark-espresso truncate flex-1">
          {{ city.name }}
        </span>
        <span class="text-[11px] text-body/50 dark:text-cream/50 shrink-0 max-w-20 truncate">
          {{ city.country }}
        </span>
        <span class="text-xs font-mono font-semibold text-forest-700 dark:text-forest-300 shrink-0 tabular-nums">
          {{ formatValue(city) }}
        </span>
      </div>
    </button>

    <!-- Show more -->
    <div v-if="hasMore" class="px-5 py-3 text-center">
      <button
        class="text-xs text-forest-600 dark:text-forest-400 hover:text-forest-700 dark:hover:text-forest-300 transition-colors cursor-pointer"
        @click="showMore"
      >
        Show more ({{ (rankedCities.length - displayCount).toLocaleString() }} remaining)
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * CityRankings - Scrollable ranked city list with horizontal bar visualization
 *
 * Filter controls live in the sidebar header (via RankingFilters).
 * This component renders only the scrollable list.
 */

import type { YearEpoch } from '../../../types/h3'
import { formatCompactNumber, formatDensity, formatArea, formatGrowthRate } from '~/utils/formatNumber'
import { toAnnualRate, YEAR_EPOCHS } from '~/composables/useGlobalStats'

const { activeStat, countryFilter, sortDirection } = useRankingFilters()
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
  growth: number | null
}

const rankedCities = computed<RankedCity[]>(() => {
  const cities: RankedCity[] = []
  const currentYear = selectedYear.value as YearEpoch
  const currentIndex = YEAR_EPOCHS.indexOf(currentYear)
  const prevYear = currentIndex > 0 ? YEAR_EPOCHS[currentIndex - 1] : null

  for (const city of allCities.value) {
    const popData = getCityPopulationData(city.id, currentYear)
    if (!popData) continue
    if (countryFilter.value && city.country !== countryFilter.value) continue

    let growth: number | null = null
    if (prevYear !== null) {
      const prevData = getCityPopulationData(city.id, prevYear)
      if (prevData && prevData.population > 0) {
        const fiveYearRate = ((popData.population - prevData.population) / prevData.population) * 100
        growth = toAnnualRate(fiveYearRate)
      }
    }

    cities.push({
      id: city.id,
      name: city.name,
      country: city.country,
      population: popData.population,
      density: popData.density_per_km2,
      area: popData.area_km2,
      growth
    })
  }

  const asc = sortDirection.value === 'asc'

  if (activeStat.value === 'growth') {
    cities.sort((a, b) => {
      if (a.growth === null && b.growth === null) return 0
      if (a.growth === null) return 1
      if (b.growth === null) return -1
      return asc ? a.growth - b.growth : b.growth - a.growth
    })
  } else {
    const stat = activeStat.value
    cities.sort((a, b) => asc ? a[stat] - b[stat] : b[stat] - a[stat])
  }

  return cities
})

const maxValue = computed(() => {
  if (!rankedCities.value.length) return 1
  if (activeStat.value === 'growth') {
    let max = 0
    for (const city of rankedCities.value) {
      if (city.growth !== null) {
        max = Math.max(max, Math.abs(city.growth))
      }
    }
    return max || 1
  }
  const stat = activeStat.value
  let max = 0
  for (const city of rankedCities.value) {
    if (city[stat] > max) max = city[stat]
  }
  return max || 1
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
    case 'growth': return formatGrowthRate(city.growth)
    default: return formatCompactNumber(city.population)
  }
}

function barPercent(city: RankedCity): string {
  if (activeStat.value === 'growth') {
    if (city.growth === null) return '0%'
    return `${(Math.abs(city.growth) / maxValue.value) * 50}%`
  }
  return `${(city[activeStat.value] / maxValue.value) * 100}%`
}

function growthBarStyle(city: RankedCity): Record<string, string> {
  const width = barPercent(city)
  if (city.growth !== null && city.growth < 0) {
    return { width, right: '50%' }
  }
  return { width, left: '50%' }
}

function growthBarColorClass(city: RankedCity): string {
  if (city.growth === null) return ''
  return city.growth >= 0
    ? 'bg-emerald-200/60 dark:bg-emerald-800/30'
    : 'bg-amber-200/60 dark:bg-amber-800/30'
}

function showMore() {
  displayCount.value += 100
}

function selectCity(id: string) {
  navigateTo(`/city/${id}`)
}

// Reset display count when filter or stat changes
watch([activeStat, countryFilter, sortDirection], () => {
  displayCount.value = 100
})
</script>

<template>
  <div>
    <button
      v-for="(city, index) in displayedCities"
      :key="city.id"
      class="w-full text-left relative py-2 px-5
             hover:bg-ink-100/30 dark:hover:bg-ink-900/20
             transition-colors cursor-pointer"
      @click="selectCity(city.id)"
    >
      <!-- Bar background — centered for growth, left-aligned for other stats -->
      <template v-if="activeStat === 'growth'">
        <div
          class="absolute inset-y-0 left-1/2 w-px bg-ink-200/50 dark:bg-ink-700/50"
        />
        <div
          class="absolute inset-y-0"
          :class="growthBarColorClass(city)"
          :style="growthBarStyle(city)"
        />
      </template>
      <div
        v-else
        class="absolute inset-y-0 left-0 bg-ink-100/60 dark:bg-ink-800/30"
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
        <span class="text-xs font-mono font-semibold text-ink-700 dark:text-ink-300 shrink-0 tabular-nums">
          {{ formatValue(city) }}
        </span>
      </div>
    </button>

    <!-- Show more -->
    <div v-if="hasMore" class="px-5 py-3 text-center">
      <button
        class="text-xs text-ink-600 dark:text-ink-400 hover:text-ink-700 dark:hover:text-ink-300 transition-colors cursor-pointer"
        @click="showMore"
      >
        Show more ({{ (rankedCities.length - displayCount).toLocaleString() }} remaining)
      </button>
    </div>
  </div>
</template>

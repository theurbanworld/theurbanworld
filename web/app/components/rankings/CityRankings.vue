<script setup lang="ts">
/**
 * CityRankings - Ranked city list with horizontal bar visualization
 *
 * Displays cities ranked by population, density, or area with
 * proportional bar graphs. Supports country filtering and
 * toggling between stats.
 */

import type { YearEpoch } from '../../../types/h3'
import { formatCompactNumber, formatDensity, formatArea } from '~/utils/formatNumber'

const emit = defineEmits<{
  close: []
}>()

const { selectedYear } = useSelectedYear()
const { allCities } = useCitiesIndex()
const { getCityPopulationData } = useCityPopulations()

type RankingStat = 'population' | 'density' | 'area'

const activeStat = ref<RankingStat>('population')
const countryFilter = ref('')
const displayCount = ref(100)

const stats: { key: RankingStat; label: string }[] = [
  { key: 'population', label: 'Population' },
  { key: 'density', label: 'Density' },
  { key: 'area', label: 'Area' }
]

// Unique countries sorted
const countries = computed(() => {
  const set = new Set(allCities.value.map(c => c.country))
  return [...set].sort()
})

// Build ranked list
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
  <div class="flex flex-col">
    <!-- Sticky controls below search notch -->
    <div class="sticky top-16 z-10 bg-parchment -mx-5 px-5 pb-3 border-b border-forest-200/40 dark:border-forest-800/40">
      <!-- Title row -->
      <div class="flex items-center justify-between mb-3">
        <h1 class="text-2xl font-bold font-crimson text-forest-700 dark:text-forest-300">
          Rankings
        </h1>
        <button
          class="shrink-0 p-1 rounded-md cursor-pointer
                 text-body/50 dark:text-cream/50
                 hover:bg-forest-100/50 dark:hover:bg-forest-900/30
                 hover:text-forest-700 dark:hover:text-forest-300
                 transition-colors"
          aria-label="Close rankings"
          @click="emit('close')"
        >
          <UIcon name="i-lucide-x" class="w-4 h-4" />
        </button>
      </div>

      <!-- Stat toggle -->
      <div class="flex gap-1 mb-3">
        <button
          v-for="stat in stats"
          :key="stat.key"
          class="flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer"
          :class="activeStat === stat.key
            ? 'bg-forest-700 text-white dark:bg-forest-400 dark:text-forest-950'
            : 'text-body/70 dark:text-cream/70 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
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
               border border-forest-200/40 dark:border-forest-800/40
               px-2 py-1.5 cursor-pointer
               focus:outline-none focus:ring-2 focus:ring-forest-300/50 dark:focus:ring-forest-700/50"
      >
        <option value="">
          All countries
        </option>
        <option v-for="c in countries" :key="c" :value="c">
          {{ c }}
        </option>
      </select>

      <!-- Count -->
      <p class="text-xs text-body/50 dark:text-cream/50 mt-2">
        {{ rankedCities.length.toLocaleString() }} cities<span v-if="countryFilter"> in {{ countryFilter }}</span>
      </p>
    </div>

    <!-- Rankings list -->
    <div class="-mx-5 mt-1">
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
  </div>
</template>

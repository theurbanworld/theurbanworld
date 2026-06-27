<script setup lang="ts">
/**
 * CityRankings - Scrollable ranked city list with horizontal bar visualization
 *
 * Filter controls live in the sidebar header (via RankingFilters).
 * This component renders only the scrollable list.
 */

import type { YearEpoch } from '../../../types/h3'
import { formatCompactNumber, formatDensity, formatArea, formatGrowthRate, formatGrowthAbs } from '~/utils/formatNumber'
import {
  COMPACTNESS_LABEL_VALUES,
  STRUCTURE_LABEL_VALUES,
  compactnessLabel,
  structureLabel,
  betaBarFraction
} from '~/utils/urbanModelLabels'
import { toAnnualRate, YEAR_EPOCHS } from '~/composables/useGlobalStats'

const { activeStat, growthMode, countryFilter, sortDirection, compactnessFilter, structureFilter } = useRankingFilters()
const { selectedYear } = useSelectedYear()
const { allCities, isLoaded: citiesLoaded } = useCitiesIndex()
const { getCityPopulationData, isLoaded: populationsLoaded } = useCityPopulations()
const { getFit } = useUrbanModelFit()

const displayCount = ref(100)

// β / R² are the Standard Urban Model "fit stats" — null-excluded and bar-encoded
// differently from the column-max stats.
const isFitStat = computed(() => activeStat.value === 'beta' || activeStat.value === 'r2')

interface RankedCity {
  id: string
  name: string
  country: string
  population: number
  density: number
  area: number
  growthRate: number | null
  growthAbs: number | null
  /** Fit metrics for the selected epoch; null when the city's fit is unreliable. */
  beta: number | null
  r2: number | null
}

/** Whether a city passes the active city-type chips (all-selected ⇒ no constraint). */
function passesCityTypeFilter(beta: number | null, r2: number | null): boolean {
  if (compactnessFilter.value.length < COMPACTNESS_LABEL_VALUES.length) {
    const label = compactnessLabel(beta)
    if (!label || !compactnessFilter.value.includes(label)) return false
  }
  if (structureFilter.value.length < STRUCTURE_LABEL_VALUES.length) {
    const label = structureLabel(r2)
    if (!label || !structureFilter.value.includes(label)) return false
  }
  return true
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

    let growthRate: number | null = null
    let growthAbs: number | null = null
    if (prevYear != null) {
      const prevData = getCityPopulationData(city.id, prevYear)
      if (prevData && prevData.population > 0) {
        const fiveYearRate = ((popData.population - prevData.population) / prevData.population) * 100
        growthRate = toAnnualRate(fiveYearRate)
        growthAbs = popData.population - prevData.population
      }
    }

    // Fit metrics are null unless the city's fit is reliable at this epoch (R16).
    const fit = getFit(city.id, currentYear)
    const reliable = !!fit?.reliable
    const beta = reliable ? fit!.beta : null
    const r2 = reliable ? fit!.r2 : null

    if (!passesCityTypeFilter(beta, r2)) continue

    cities.push({
      id: city.id,
      name: city.name,
      country: city.country,
      population: popData.population,
      density: popData.density_per_km2,
      area: popData.area_km2,
      growthRate,
      growthAbs,
      beta,
      r2
    })
  }

  // Metric sorts exclude cities without a reliable fit at this epoch (R16).
  let result = cities
  if (activeStat.value === 'beta') result = cities.filter(c => c.beta !== null)
  else if (activeStat.value === 'r2') result = cities.filter(c => c.r2 !== null)

  const asc = sortDirection.value === 'asc'

  if (activeStat.value === 'growth') {
    const field = growthMode.value === 'rate' ? 'growthRate' as const : 'growthAbs' as const
    result.sort((a, b) => {
      if (a[field] === null && b[field] === null) return 0
      if (a[field] === null) return 1
      if (b[field] === null) return -1
      return asc ? a[field]! - b[field]! : b[field]! - a[field]!
    })
  } else if (activeStat.value === 'beta' || activeStat.value === 'r2') {
    const stat = activeStat.value
    result.sort((a, b) => asc ? a[stat]! - b[stat]! : b[stat]! - a[stat]!)
  } else {
    const stat = activeStat.value
    result.sort((a, b) => asc ? a[stat] - b[stat] : b[stat] - a[stat])
  }

  return result
})

// How many cities are hidden from a metric sort because they lack a reliable fit
// (so the visible-count shrink is explained, not silent).
const unreliableHiddenCount = computed(() => {
  if (!isFitStat.value) return 0
  const year = selectedYear.value as YearEpoch
  let n = 0
  for (const city of allCities.value) {
    if (!getCityPopulationData(city.id, year)) continue
    if (countryFilter.value && city.country !== countryFilter.value) continue
    if (!getFit(city.id, year)?.reliable) n++
  }
  return n
})

const maxValue = computed(() => {
  if (!rankedCities.value.length) return 1
  // Fit stats are bar-encoded against their own scales, not the column max.
  if (isFitStat.value) return 1
  if (activeStat.value === 'growth') {
    const field = growthMode.value === 'rate' ? 'growthRate' as const : 'growthAbs' as const
    let max = 0
    for (const city of rankedCities.value) {
      if (city[field] !== null) max = Math.max(max, Math.abs(city[field]))
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

// The rankings need both the cities index and population data, which now load
// on the client. Show a skeleton until both resolve, then fall back to an empty
// state if the active filter matches no cities.
const isLoading = computed(() => !citiesLoaded.value || !populationsLoaded.value)

// Placeholder rows for the loading skeleton (descending widths echo a ranked
// list tapering off).
const SKELETON_WIDTHS = ['92%', '88%', '81%', '76%', '70%', '64%', '58%', '52%', '47%', '43%', '38%', '34%']

function formatValue(city: RankedCity): string {
  switch (activeStat.value) {
    case 'density': return formatDensity(city.density)
    case 'area': return formatArea(city.area)
    case 'growth':
      return growthMode.value === 'rate'
        ? formatGrowthRate(city.growthRate)
        : formatGrowthAbs(city.growthAbs)
    case 'beta': return city.beta != null ? city.beta.toFixed(3) : '—'
    case 'r2': return city.r2 != null ? city.r2.toFixed(2) : '—'
    default: return formatCompactNumber(city.population)
  }
}

function growthValue(city: RankedCity): number | null {
  return growthMode.value === 'rate' ? city.growthRate : city.growthAbs
}

function barPercent(city: RankedCity): string {
  if (activeStat.value === 'growth') {
    const v = growthValue(city)
    if (v === null) return '0%'
    return `${(Math.abs(v) / maxValue.value) * 50}%`
  }
  // β: scaled within the compactness band range (column max is meaningless here).
  if (activeStat.value === 'beta') return `${betaBarFraction(city.beta) * 100}%`
  // R²: a direct 0–1 fill.
  if (activeStat.value === 'r2') return `${Math.max(0, Math.min(1, city.r2 ?? 0)) * 100}%`
  const stat = activeStat.value as 'population' | 'density' | 'area'
  return `${(city[stat] / maxValue.value) * 100}%`
}

function growthBarStyle(city: RankedCity): Record<string, string> {
  const width = barPercent(city)
  const v = growthValue(city)
  if (v !== null && v < 0) {
    return { width, right: '50%' }
  }
  return { width, left: '50%' }
}

function growthBarColorClass(city: RankedCity): string {
  const v = growthValue(city)
  if (v === null) return ''
  return v >= 0
    ? 'bg-emerald-200/60 dark:bg-emerald-800/30'
    : 'bg-amber-200/60 dark:bg-amber-800/30'
}

function showMore() {
  displayCount.value += 100
}

function selectCity(id: string) {
  navigateTo(`/city/${id}`)
}

// Reset display count when filter, stat, or growth mode changes
watch(
  [activeStat, growthMode, countryFilter, sortDirection, compactnessFilter, structureFilter, selectedYear],
  () => {
    displayCount.value = 100
  }
)
</script>

<template>
  <div>
    <!-- Fit-stat affordance: epoch scope + explained shrink -->
    <p
      v-if="isFitStat"
      data-testid="fit-stat-note"
      class="px-5 pt-2 pb-1 text-[11px] text-body/50 dark:text-cream/50"
    >
      {{ activeStat === 'beta' ? 'Compactness' : 'Monocentricity' }} (at {{ selectedYear }})<span
        v-if="unreliableHiddenCount > 0"
      > · {{ unreliableHiddenCount.toLocaleString() }} without a reliable fit hidden</span>
    </p>

    <!-- Loading skeleton — shown while the index + population datasets stream in -->
    <div
      v-if="isLoading"
      aria-busy="true"
      aria-label="Loading city rankings"
      class="animate-pulse"
    >
      <div
        v-for="(width, i) in SKELETON_WIDTHS"
        :key="i"
        class="relative py-2 px-5"
      >
        <!-- Faint bar echoing the ranked value bar -->
        <div
          class="absolute inset-y-0 left-0 bg-ink-100/40 dark:bg-ink-800/20"
          :style="{ width }"
        />
        <div class="relative flex items-baseline gap-2">
          <span class="w-6 shrink-0" />
          <span class="h-3 rounded bg-ink-200/50 dark:bg-ink-700/40 flex-1 max-w-32" />
          <span class="h-3 w-12 rounded bg-ink-200/40 dark:bg-ink-700/30 shrink-0 ml-auto" />
        </div>
      </div>
    </div>

    <!-- Empty state — data loaded but the active filter matches nothing (e.g. a
         city-type chip + epoch matching no reliable city) -->
    <div
      v-else-if="!displayedCities.length"
      data-testid="rankings-empty"
      class="px-5 py-10 text-center"
    >
      <p class="text-sm text-body/50 dark:text-cream/50">
        No cities match these filters at {{ selectedYear }}.
      </p>
    </div>

    <!-- Ranked list -->
    <template v-else>
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
      <div
        v-if="hasMore"
        class="px-5 py-3 text-center"
      >
        <button
          class="text-xs text-ink-600 dark:text-ink-400 hover:text-ink-700 dark:hover:text-ink-300 transition-colors cursor-pointer"
          @click="showMore"
        >
          Show more ({{ (rankedCities.length - displayCount).toLocaleString() }} remaining)
        </button>
      </div>
    </template>
  </div>
</template>

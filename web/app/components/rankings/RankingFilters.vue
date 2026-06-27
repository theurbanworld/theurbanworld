<script setup lang="ts">
/**
 * RankingFilters - Country filter, city count, and sort toggle for rankings
 *
 * Rendered in the sidebar header (non-scrollable section).
 * The stat toggle buttons (Population/Density/Area/Growth) live in the
 * StatToggle component in the search strip, not here.
 */

import type { YearEpoch } from '../../../types/h3'
import { useDataset } from '~/composables/useDataset'
import {
  COMPACTNESS_LABEL_VALUES,
  STRUCTURE_LABEL_VALUES,
  type CompactnessLabel,
  type StructureLabel
} from '~/utils/urbanModelLabels'

const { countryFilter, sortDirection, compactnessFilter, structureFilter } = useRankingFilters()
const { selectedYear } = useSelectedYear()
const { allCities } = useCitiesIndex()
const { getCityPopulationData } = useCityPopulations()

// City-type chips only apply where the fit data exists (radial dataset).
const { hasFeatureComputed } = useDataset()
const showCityType = hasFeatureComputed('radialProfiles')

const compactnessOptions = COMPACTNESS_LABEL_VALUES
const structureOptions = STRUCTURE_LABEL_VALUES

function toggleCompactness(label: CompactnessLabel) {
  compactnessFilter.value = compactnessFilter.value.includes(label)
    ? compactnessFilter.value.filter(l => l !== label)
    : [...compactnessFilter.value, label]
}

function toggleStructure(label: StructureLabel) {
  structureFilter.value = structureFilter.value.includes(label)
    ? structureFilter.value.filter(l => l !== label)
    : [...structureFilter.value, label]
}

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
      <option
        v-for="c in countries"
        :key="c"
        :value="c"
      >
        {{ c }}
      </option>
    </select>

    <!-- City-type filter (Standard Urban Model) -->
    <div
      v-if="showCityType"
      data-testid="city-type-filter"
      class="mt-2 flex flex-wrap items-center gap-1"
    >
      <button
        v-for="label in compactnessOptions"
        :key="label"
        class="px-2 py-0.5 text-[11px] rounded-full border transition-colors cursor-pointer"
        :class="compactnessFilter.includes(label)
          ? 'bg-ink-700 text-white border-ink-700 dark:bg-ink-400 dark:text-ink-950 dark:border-ink-400'
          : 'text-body/60 dark:text-cream/60 border-ink-200/60 dark:border-ink-800/60 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
        @click="toggleCompactness(label)"
      >
        {{ label }}
      </button>
      <span class="mx-1 text-ink-200 dark:text-ink-800">·</span>
      <button
        v-for="label in structureOptions"
        :key="label"
        class="px-2 py-0.5 text-[11px] rounded-full border transition-colors cursor-pointer"
        :class="structureFilter.includes(label)
          ? 'bg-ink-700 text-white border-ink-700 dark:bg-ink-400 dark:text-ink-950 dark:border-ink-400'
          : 'text-body/60 dark:text-cream/60 border-ink-200/60 dark:border-ink-800/60 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
        @click="toggleStructure(label)"
      >
        {{ label }}
      </button>
    </div>

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

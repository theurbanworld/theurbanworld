<script setup lang="ts">
/**
 * EyebrowPanel - Right-anchored panel with epoch controls and global statistics
 *
 * Drops down vertically from the top-right of the map area.
 * Visibility is controlled by useEyebrowPanel (toggle lives in the search strip).
 */

import { useSelectedYear } from '../../composables/useSelectedYear'
import { useGlobalStats } from '../../composables/useGlobalStats'
import { useEyebrowPanel } from '../../composables/useEyebrowPanel'

// Constants for epoch range
const MIN_YEAR = 1975
const MAX_YEAR = 2030
const STEP = 5

// Composables for state
const { selectedYear, setYear } = useSelectedYear()
const {
  worldPopulation,
  worldPopulationRaw,
  worldPopulationTrendPrevious,
  worldPopulationTrendNext,
  urbanPopulation,
  urbanPopulationRaw,
  urbanPopulationTrendPrevious,
  urbanPopulationTrendNext,
  urbanPercentageOfWorld,
  datasetUrbanPopulation
} = useGlobalStats()
const { isExpanded } = useEyebrowPanel()

// Two-way binding for slider
const sliderValue = computed({
  get: () => selectedYear.value,
  set: (value: number) => {
    const snappedYear = Math.round(value / STEP) * STEP
    const clampedYear = Math.max(MIN_YEAR, Math.min(MAX_YEAR, snappedYear))
    setYear(clampedYear)
  }
})
</script>

<template>
  <div
    v-if="isExpanded"
    data-testid="eyebrow-panel"
    class="absolute z-100 right-0 top-0 p-4 rounded-bl-xl shadow-lg
           bg-parchment/95 backdrop-blur-sm
           w-70 max-sm:w-auto max-sm:min-w-40"
  >
    <!-- Epoch Slider -->
    <div class="px-1">
      <USlider
        v-model="sliderValue"
        :min="MIN_YEAR"
        :max="MAX_YEAR"
        :step="STEP"
        data-testid="epoch-slider"
        class="epoch-slider"
      />
    </div>

    <!-- Year labels (compact) -->
    <div class="flex justify-between mt-1 mb-4 px-1">
      <span class="font-mono text-xs text-body/50 dark:text-cream/50">{{ MIN_YEAR }}</span>
      <span class="font-mono text-xs text-body/50 dark:text-cream/50">{{ MAX_YEAR }}</span>
    </div>

    <!-- Divider - hidden on small screens -->
    <hr class="border-border/30 dark:border-cream/20 mb-4 max-sm:hidden">

    <!-- World Population - hidden on small screens -->
    <div class="max-sm:hidden">
      <DataPoint
        id="world-population"
        label="World Population"
        :value="worldPopulation"
        :raw-value="worldPopulationRaw"
        :trend-previous="worldPopulationTrendPrevious"
        :trend-next="worldPopulationTrendNext"
        source-label="Source: UN WPP"
        content-path="/data/source-un-wpp"
      />

      <!-- Spacer -->
      <div class="h-4" />

      <!-- Urban Population (UN official, with dataset coverage context) -->
      <DataPoint
        id="urban-population"
        label="Urban Population"
        :value="urbanPopulation"
        :raw-value="urbanPopulationRaw"
        :trend-previous="urbanPopulationTrendPrevious"
        :trend-next="urbanPopulationTrendNext"
        :percentage-value="urbanPercentageOfWorld"
        percentage-label="of"
        percentage-ref-label="World Population"
        percentage-ref-id="world-population"
        source-label="Source: UN WUP"
        content-path="/data/source-un-wup"
      >
        <!-- Dataset coverage context -->
        <div class="flex items-center gap-1 mt-1">
          <span class="font-mono text-xs font-medium text-ink-600/70 dark:text-ink-400/70">
            {{ datasetUrbanPopulation }}
          </span>
          <span class="text-xs text-body/50 dark:text-cream/50">
            in our dataset
          </span>
        </div>
      </DataPoint>
    </div>
  </div>
</template>

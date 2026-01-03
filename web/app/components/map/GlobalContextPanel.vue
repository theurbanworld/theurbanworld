<template>
  <div
    data-testid="global-context-panel"
    class="absolute z-100 p-4 rounded-xl shadow-lg bg-parchment/95 dark:bg-espresso/95 backdrop-blur-sm
           right-4 top-4 w-56
           max-sm:right-2 max-sm:top-2 max-sm:w-auto max-sm:min-w-40"
  >
    <!-- Epoch Year Display -->
    <div class="text-center mb-3">
      <span
        data-testid="epoch-year"
        class="font-mono text-4xl max-sm:text-3xl font-bold text-forest-700 dark:text-forest-300 tracking-wide"
      >
        {{ selectedYear }}
      </span>
    </div>

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
      />

      <!-- Spacer -->
      <div class="h-4" />

      <!-- Urban Population -->
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
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * GlobalContextPanel - Right-side panel with epoch controls and global statistics
 *
 * Displays the current epoch year, a slider to change epochs, and
 * global population data points (world and urban population).
 * Positioned fixed on the right side of the viewport.
 * On mobile, shows only year and slider; data points are hidden.
 */

import { useSelectedYear } from '../../composables/useSelectedYear'
import { useGlobalStats } from '../../composables/useGlobalStats'

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
  urbanPercentageOfWorld
} = useGlobalStats()

// Two-way binding for slider
const sliderValue = computed({
  get: () => selectedYear.value,
  set: (value: number) => {
    // Snap to nearest epoch
    const snappedYear = Math.round(value / STEP) * STEP
    const clampedYear = Math.max(MIN_YEAR, Math.min(MAX_YEAR, snappedYear))
    setYear(clampedYear)
  }
})
</script>

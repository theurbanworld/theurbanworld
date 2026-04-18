<script setup lang="ts">
/**
 * ComparisonMetricTable — Side-by-side metric comparison for two cities
 *
 * Shows population, density, area, and growth rate with the
 * larger value highlighted per row. Uses city A/B identity colors.
 */

import { useCityStats } from '~/composables/useCityStats'
import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'

const props = defineProps<{
  cityIdA: string
  cityIdB: string
}>()

const statsA = useCityStats(computed(() => props.cityIdA))
const statsB = useCityStats(computed(() => props.cityIdB))

const isLoading = computed(() => statsA.isLoading.value || statsB.isLoading.value)

interface MetricRow {
  label: string
  valueA: string
  valueB: string
  rawA: number
  rawB: number
}

const metrics = computed<MetricRow[]>(() => [
  {
    label: 'Population',
    valueA: statsA.populationHumanized.value,
    valueB: statsB.populationHumanized.value,
    rawA: statsA.populationRaw.value,
    rawB: statsB.populationRaw.value
  },
  {
    label: 'Density',
    valueA: statsA.densityFormatted.value,
    valueB: statsB.densityFormatted.value,
    rawA: statsA.density.value,
    rawB: statsB.density.value
  },
  {
    label: 'Area',
    valueA: statsA.areaFormatted.value,
    valueB: statsB.areaFormatted.value,
    rawA: statsA.area.value,
    rawB: statsB.area.value
  }
])

function isLarger(rawA: number, rawB: number, side: 'A' | 'B'): boolean {
  if (rawA === rawB) return false
  return side === 'A' ? rawA > rawB : rawB > rawA
}
</script>

<template>
  <div data-testid="comparison-metric-table">
    <!-- Loading skeleton -->
    <div
      v-if="isLoading"
      class="space-y-3"
    >
      <div
        v-for="i in 3"
        :key="i"
        class="flex gap-3"
      >
        <div class="flex-1 h-12 bg-muted rounded animate-pulse" />
        <div class="flex-1 h-12 bg-muted rounded animate-pulse" />
      </div>
    </div>

    <!-- Metric rows -->
    <div
      v-else
      class="space-y-2"
    >
      <div
        v-for="metric in metrics"
        :key="metric.label"
        class="grid grid-cols-[auto_1fr_1fr] gap-x-3 items-baseline"
      >
        <!-- Row label -->
        <span class="text-xs text-body/60 dark:text-cream/60 w-16">
          {{ metric.label }}
        </span>

        <!-- City A value -->
        <div class="text-right">
          <span
            class="font-mono text-sm"
            :class="isLarger(metric.rawA, metric.rawB, 'A')
              ? 'font-semibold ' + CITY_A_COLOR.textClass
              : 'text-body/70 dark:text-cream/70'"
          >
            {{ metric.valueA }}
          </span>
        </div>

        <!-- City B value -->
        <div class="text-right">
          <span
            class="font-mono text-sm"
            :class="isLarger(metric.rawA, metric.rawB, 'B')
              ? 'font-semibold ' + CITY_B_COLOR.textClass
              : 'text-body/70 dark:text-cream/70'"
          >
            {{ metric.valueB }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ComparisonMetricTable — Side-by-side metric comparison for two cities
 *
 * Shows population, density, area, and growth rate with the
 * larger value highlighted per row. Uses city A/B identity colors.
 */

import { useCityStats } from '~/composables/useCityStats'
import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'
import { compactnessLabel, structureLabel } from '~/utils/urbanModelLabels'

const props = defineProps<{
  cityIdA: string
  cityIdB: string
}>()

const statsA = useCityStats(computed(() => props.cityIdA))
const statsB = useCityStats(computed(() => props.cityIdB))

const { selectedYear } = useSelectedYear()
const { getFit } = useUrbanModelFit()
const fitA = computed(() => getFit(props.cityIdA, selectedYear.value))
const fitB = computed(() => getFit(props.cityIdB, selectedYear.value))
const reliableA = computed(() => !!fitA.value?.reliable)
const reliableB = computed(() => !!fitB.value?.reliable)

const isLoading = computed(() => statsA.isLoading.value || statsB.isLoading.value)

interface MetricRow {
  label: string
  valueA: string
  valueB: string
  /** null when that city's fit is unreliable — shown as a dash, never highlighted. */
  rawA: number | null
  rawB: number | null
}

interface CategoricalRow {
  label: string
  labelA: string | null
  labelB: string | null
}

const baseMetrics = computed<MetricRow[]>(() => [
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

// β and R² as numeric rows — keep the larger-value highlighting; dash + no highlight
// for a city whose fit is unreliable at this epoch.
const fitMetrics = computed<MetricRow[]>(() => [
  {
    label: 'Compactness (β)',
    valueA: reliableA.value ? fitA.value!.beta!.toFixed(3) : '—',
    valueB: reliableB.value ? fitB.value!.beta!.toFixed(3) : '—',
    rawA: reliableA.value ? fitA.value!.beta! : null,
    rawB: reliableB.value ? fitB.value!.beta! : null
  },
  {
    label: 'Model fit (R²)',
    valueA: reliableA.value ? fitA.value!.r2!.toFixed(2) : '—',
    valueB: reliableB.value ? fitB.value!.r2!.toFixed(2) : '—',
    rawA: reliableA.value ? fitA.value!.r2! : null,
    rawB: reliableB.value ? fitB.value!.r2! : null
  }
])

const numericRows = computed<MetricRow[]>(() => [...baseMetrics.value, ...fitMetrics.value])

// Derived labels are categorical: no larger-value highlighting, dash when unreliable.
const fitLabels = computed<CategoricalRow[]>(() => [
  {
    label: 'Compactness',
    labelA: reliableA.value ? compactnessLabel(fitA.value!.beta) : null,
    labelB: reliableB.value ? compactnessLabel(fitB.value!.beta) : null
  },
  {
    label: 'Structure',
    labelA: reliableA.value ? structureLabel(fitA.value!.r2) : null,
    labelB: reliableB.value ? structureLabel(fitB.value!.r2) : null
  }
])

function isLarger(rawA: number | null, rawB: number | null, side: 'A' | 'B'): boolean {
  if (rawA == null || rawB == null || rawA === rawB) return false
  return side === 'A' ? rawA > rawB : rawB > rawA
}

/** Categorical rows are never "larger"; both-equal gets a subtle muted treatment. */
function labelClass(row: CategoricalRow, side: 'A' | 'B'): string {
  const value = side === 'A' ? row.labelA : row.labelB
  if (value == null) return 'text-body/40 dark:text-cream/40'
  const same = row.labelA != null && row.labelA === row.labelB
  return same ? 'text-body/50 dark:text-cream/50' : 'text-body/70 dark:text-cream/70'
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
      class="divide-y divide-border/30 dark:divide-border/20"
    >
      <!-- Numeric rows (population/density/area + β/R²): larger value highlighted -->
      <div
        v-for="metric in numericRows"
        :key="metric.label"
        class="grid grid-cols-[auto_1fr_1fr] gap-x-3 items-baseline py-2"
      >
        <!-- Row label -->
        <span class="text-xs font-semibold uppercase tracking-wider text-body/60 dark:text-cream/60 w-20">
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

      <!-- Categorical label rows (compactness/structure): no larger-value highlight -->
      <div
        v-for="row in fitLabels"
        :key="row.label"
        data-testid="comparison-label-row"
        class="grid grid-cols-[auto_1fr_1fr] gap-x-3 items-baseline"
      >
        <span class="text-xs text-body/60 dark:text-cream/60 w-16">
          {{ row.label }}
        </span>
        <div class="text-right">
          <span
            class="text-sm"
            :class="labelClass(row, 'A')"
          >
            {{ row.labelA ?? '—' }}
          </span>
        </div>
        <div class="text-right">
          <span
            class="text-sm"
            :class="labelClass(row, 'B')"
          >
            {{ row.labelB ?? '—' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

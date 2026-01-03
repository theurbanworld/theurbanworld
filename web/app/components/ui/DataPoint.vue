<template>
  <div class="flex flex-col gap-0.5">
    <!-- Label -->
    <span
      data-testid="datapoint-label"
      class="text-xs text-body/70 dark:text-cream/70"
    >
      {{ label }}
    </span>

    <!-- Value with tooltip -->
    <UTooltip :text="formattedRawValue">
      <div
        data-testid="datapoint-value-wrapper"
        class="cursor-help"
      >
        <span
          data-testid="datapoint-value"
          class="font-mono text-2xl font-semibold text-forest-700 dark:text-forest-300"
        >
          {{ value }}
        </span>
      </div>
    </UTooltip>

    <!-- Source link -->
    <span
      data-testid="datapoint-source"
      class="text-xs text-body/50 dark:text-cream/50 hover:text-forest-600 dark:hover:text-forest-400 cursor-pointer transition-colors"
    >
      {{ sourceLabel || 'Source' }}
    </span>
  </div>
</template>

<script setup lang="ts">
/**
 * DataPoint - Reusable data display component
 *
 * Displays a labeled data value with humanized format and exact value tooltip.
 * Designed for displaying population statistics and similar numeric data.
 * Uses mono font for values and sans-serif for labels per typography guidelines.
 */

import { formatExactNumber } from '../../composables/useGlobalStats'

interface Props {
  /** Small label text (e.g., "World Population") */
  label: string
  /** Humanized display value (e.g., "8.2 billion") */
  value: string
  /** Exact numeric value for tooltip (e.g., 8191988536) */
  rawValue: number
  /** Source link text (defaults to "Source") */
  sourceLabel?: string
}

const props = defineProps<Props>()

/**
 * Format raw value for tooltip display with locale-aware separators
 */
const formattedRawValue = computed(() => {
  return formatExactNumber(props.rawValue)
})
</script>

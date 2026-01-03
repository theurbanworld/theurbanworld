<template>
  <div class="flex flex-col gap-0.5">
    <!-- Label -->
    <span
      data-testid="datapoint-label"
      class="text-xs text-body/70 dark:text-cream/70"
    >
      {{ label }}
    </span>

    <!-- Value row with optional trend indicator -->
    <div class="flex items-center gap-2">
      <!-- Trend indicator (if trend data provided) -->
      <UTooltip v-if="showTrend" :text="trendTooltip">
        <UIcon
          data-testid="datapoint-trend-icon"
          :name="trendInfo.icon"
          :class="['w-5 h-5 shrink-0 transition-transform', trendInfo.colorClass]"
          :style="{ transform: `rotate(${trendInfo.rotation}deg)` }"
        />
      </UTooltip>

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
    </div>

    <!-- Percentage row (if percentage data provided) -->
    <div v-if="percentageValue !== undefined" class="flex items-center gap-1">
      <span
        data-testid="datapoint-percentage"
        class="font-mono text-sm font-medium text-forest-600 dark:text-forest-400"
      >
        {{ formattedPercentage }}
      </span>
      <span
        v-if="percentageLabel"
        data-testid="datapoint-percentage-label"
        class="text-xs text-body/60 dark:text-cream/60"
      >
        {{ percentageLabel }}
      </span>
    </div>

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
 * Optionally shows trend indicators (direction arrows) and percentage context.
 * Designed for displaying population statistics and similar numeric data.
 * Uses mono font for values and sans-serif for labels per typography guidelines.
 */

import { formatExactNumber, getTrendInfo, type TrendInfo } from '../../composables/useGlobalStats'

interface Props {
  /** Small label text (e.g., "World Population") */
  label: string
  /** Humanized display value (e.g., "8.2 billion") */
  value: string
  /** Exact numeric value for tooltip (e.g., 8191988536) */
  rawValue: number
  /** Source link text (defaults to "Source") */
  sourceLabel?: string
  /** Percentage change from previous epoch (null if no previous exists) */
  trendPrevious?: number | null
  /** Percentage change to next epoch (null if no next exists) */
  trendNext?: number | null
  /** Percentage value to display (e.g., 43.6 for "43.6%") */
  percentageValue?: number
  /** Label for the percentage (e.g., "of World Population") */
  percentageLabel?: string
}

const props = defineProps<Props>()

/**
 * Format raw value for tooltip display with locale-aware separators
 */
const formattedRawValue = computed(() => {
  return formatExactNumber(props.rawValue)
})

/**
 * Determine consensus trend direction
 * - If both previous and next agree on direction → use average magnitude
 * - If they disagree → return 0 (stable)
 * - Edge cases: use whichever is available
 */
const trendDirection = computed((): number | null => {
  const prev = props.trendPrevious
  const next = props.trendNext

  // No trend data provided
  if (prev === undefined && next === undefined) return null

  // Edge case: only previous available (at 2030)
  if (next === null && prev !== undefined && prev !== null) return prev

  // Edge case: only next available (at 1975)
  if (prev === null && next !== undefined && next !== null) return next

  // Both are null or undefined
  if ((prev === null || prev === undefined) && (next === null || next === undefined)) return null

  // Both have values - check for consensus
  const prevValue = prev as number
  const nextValue = next as number
  const prevUp = prevValue > 0
  const nextUp = nextValue > 0

  if (prevUp === nextUp) {
    // They agree on direction - use average magnitude
    return (prevValue + nextValue) / 2
  }

  // They disagree - show stable/flat
  return 0
})

/**
 * Whether to show the trend indicator
 */
const showTrend = computed(() => trendDirection.value !== null)

/**
 * Get trend display info (icon, color) based on trend direction
 */
const trendInfo = computed((): TrendInfo => {
  if (trendDirection.value === null) {
    return { level: 'stable', icon: 'i-lucide-minus', colorClass: 'text-gray-400' }
  }
  return getTrendInfo(trendDirection.value)
})

/**
 * Tooltip text for trend indicator
 */
const trendTooltip = computed(() => {
  if (trendDirection.value === null) return ''
  const sign = trendDirection.value >= 0 ? '+' : ''
  return `${sign}${trendDirection.value.toFixed(1)}% per epoch`
})

/**
 * Formatted percentage string (e.g., "43.6%")
 */
const formattedPercentage = computed(() => {
  if (props.percentageValue === undefined) return ''
  return `${props.percentageValue.toFixed(1)}%`
})
</script>

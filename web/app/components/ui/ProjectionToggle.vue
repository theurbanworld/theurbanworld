<script setup lang="ts">
/**
 * ProjectionToggle — a now/future control for a projection-class metric.
 *
 * Renders two catalog-provided values (now, future) with a toggle between them
 * and an always-visible "modeled, not measured" qualifier. There is NO implied
 * interpolation between the two points — they are distinct scenarios, not a trend.
 * Categorical values (e.g. Köppen class codes) pass through as strings.
 */

import { formatClimateValue, MODELED_QUALIFIER } from '../../utils/climateFormat'

const props = defineProps<{
  now: number | string | null
  future: number | string | null
  /** Label for the future scenario, e.g. "2070, SSP5-8.5". */
  futureLabel?: string
  unit?: string | null
  nowLabel?: string
}>()

const mode = ref<'now' | 'future'>('now')

const activeValue = computed(() => (mode.value === 'now' ? props.now : props.future))
const display = computed(() => formatClimateValue(activeValue.value, props.unit ?? null))
const futureText = computed(() => props.futureLabel ?? 'projected')
</script>

<template>
  <div class="flex flex-col gap-1">
    <!-- now / future toggle -->
    <div class="flex gap-2 text-[10px] font-mono">
      <button
        data-testid="projection-now"
        class="transition-colors cursor-pointer"
        :class="mode === 'now'
          ? 'text-ink-600 dark:text-ink-400'
          : 'text-body/30 dark:text-cream/30 hover:text-body/50 dark:hover:text-cream/50'"
        @click="mode = 'now'"
      >
        {{ nowLabel ?? 'now' }}
      </button>
      <button
        data-testid="projection-future"
        class="transition-colors cursor-pointer"
        :class="mode === 'future'
          ? 'text-ink-600 dark:text-ink-400'
          : 'text-body/30 dark:text-cream/30 hover:text-body/50 dark:hover:text-cream/50'"
        @click="mode = 'future'"
      >
        {{ futureText }}
      </button>
    </div>

    <span
      data-testid="projection-value"
      class="font-mono text-2xl font-semibold text-ink-700 dark:text-ink-300"
    >
      {{ display }}
    </span>

    <!-- modeled honesty qualifier, always visible -->
    <span
      data-testid="projection-modeled"
      class="text-[10px] italic text-body/50 dark:text-cream/50"
    >
      {{ MODELED_QUALIFIER }}
    </span>
  </div>
</template>

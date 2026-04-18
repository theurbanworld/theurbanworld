<script setup lang="ts">
/**
 * EpochStrip - Inline epoch year + slider for the controls strip
 *
 * Shows the selected year on the left, slider on the right.
 * Designed to sit inline within the full-width controls bar.
 */

const MIN_YEAR = 1975
const MAX_YEAR = 2030
const STEP = 5

const { selectedYear, setYear } = useSelectedYear()

const sliderValue = computed({
  get: () => selectedYear.value,
  set: (value: number) => {
    const snapped = Math.round(value / STEP) * STEP
    setYear(Math.max(MIN_YEAR, Math.min(MAX_YEAR, snapped)))
  }
})
</script>

<template>
  <div class="flex items-center gap-3 w-full">
    <span class="font-mono text-xl font-bold text-ink-700 dark:text-ink-300 tracking-wide shrink-0">
      {{ selectedYear }}
    </span>
    <div class="flex items-center gap-2 flex-1 min-w-0">
      <span class="font-mono text-[10px] text-body/40 dark:text-cream/40 shrink-0">{{ MIN_YEAR }}</span>
      <input
        v-model.number="sliderValue"
        type="range"
        :min="MIN_YEAR"
        :max="MAX_YEAR"
        :step="STEP"
        class="flex-1 min-w-0 h-1.5 appearance-none rounded-full cursor-pointer
               bg-ink-200 dark:bg-ink-700
               accent-ink-600 dark:accent-ink-400"
        data-testid="epoch-slider"
      >
      <span class="font-mono text-[10px] text-body/40 dark:text-cream/40 shrink-0">{{ MAX_YEAR }}</span>
    </div>
  </div>
</template>

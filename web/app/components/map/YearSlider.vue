<template>
  <div class="year-slider">
    <!-- Current year display -->
    <div class="year-display">
      <span class="year-value">{{ selectedYear }}</span>
    </div>

    <!-- Slider track with labels -->
    <div class="slider-container">
      <USlider
        :model-value="sliderValue"
        :min="MIN_YEAR"
        :max="MAX_YEAR"
        :step="STEP"
        class="slider-track"
        @update:model-value="onYearChange"
      />

      <!-- Year epoch labels -->
      <div class="year-labels">
        <span
          v-for="year in displayLabels"
          :key="year"
          class="year-label"
          :class="{ 'year-label--active': year === selectedYear }"
          :style="{ left: getLabelPosition(year) }"
          @click="setYear(year)"
        >
          {{ year }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * YearSlider - Timeline slider for year epoch selection
 *
 * Positioned at bottom center of viewport.
 * Allows users to scrub through years 1975-2030 in 5-year increments.
 * Snaps immediately to epochs with no smooth transitions.
 */

import type { YearEpoch } from '../../../types/h3'

// Year range configuration as constants
const MIN_YEAR = 1975
const MAX_YEAR = 2030
const STEP = 5
const RANGE = MAX_YEAR - MIN_YEAR

// Labels to display below slider (subset for readability)
const displayLabels: YearEpoch[] = [1975, 1985, 1995, 2005, 2015, 2025]

// Use the shared year state
const { selectedYear, setYear } = useSelectedYear()

// Slider value as a plain number for USlider binding
const sliderValue = computed(() => selectedYear.value as number)

/**
 * Handle slider value change
 * Snaps to nearest 5-year epoch immediately
 */
function onYearChange(value: number | number[] | undefined) {
  if (value === undefined) return

  // Handle both single value and array (USlider can emit either)
  const numValue = Array.isArray(value) ? value[0] : value

  if (numValue === undefined) return

  // Snap to nearest epoch
  const snappedYear = Math.round(numValue / STEP) * STEP

  // Clamp to valid range
  const clampedYear = Math.max(MIN_YEAR, Math.min(MAX_YEAR, snappedYear))

  setYear(clampedYear)
}

/**
 * Calculate position for a year label as percentage
 */
function getLabelPosition(year: number): string {
  const position = ((year - MIN_YEAR) / RANGE) * 100
  return `${position}%`
}
</script>

<style scoped>
.year-slider {
  position: fixed;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 60vw;
  max-width: 600px;
  min-width: 280px;
  z-index: 100;
  padding: 12px 20px 24px;
  background-color: rgba(245, 241, 230, 0.95); /* Parchment with opacity */
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(74, 66, 56, 0.15);
}

/* Dark mode support */
:global(.dark) .year-slider {
  background-color: rgba(61, 53, 44, 0.95); /* Espresso with opacity */
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.year-display {
  text-align: center;
  margin-bottom: 8px;
}

.year-value {
  font-family: var(--font-mono), 'JetBrains Mono', monospace;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--color-forest-700, #3A5233);
  letter-spacing: 0.05em;
}

:global(.dark) .year-value {
  color: var(--color-forest-300, #B5C9AF);
}

.slider-container {
  position: relative;
  padding-bottom: 20px;
}

/* Slider styling via deep selector to customize USlider */
.slider-track {
  width: 100%;
}

/* Style the slider track */
:deep([data-part="track"]) {
  background-color: var(--color-border, #9A9385);
  height: 8px;
  border-radius: 4px;
}

:global(.dark) :deep([data-part="track"]) {
  background-color: rgba(154, 147, 133, 0.5);
}

/* Style the filled range */
:deep([data-part="range"]) {
  background-color: var(--color-forest-600, #4A6741);
}

:global(.dark) :deep([data-part="range"]) {
  background-color: var(--color-forest-500, #6A8F5E);
}

/* Style the thumb */
:deep([data-part="thumb"]) {
  width: 20px;
  height: 20px;
  background-color: var(--color-forest-600, #4A6741);
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  cursor: grab;
  transition: background-color 0.15s ease, transform 0.15s ease;
}

:deep([data-part="thumb"]:hover) {
  background-color: var(--color-forest-700, #3A5233);
  transform: scale(1.1);
}

:deep([data-part="thumb"]:active) {
  cursor: grabbing;
}

:global(.dark) :deep([data-part="thumb"]) {
  background-color: var(--color-forest-500, #6A8F5E);
  border-color: var(--color-espresso, #3D352C);
}

:global(.dark) :deep([data-part="thumb"]:hover) {
  background-color: var(--color-forest-400, #8FAD85);
}

/* Year labels container */
.year-labels {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 20px;
}

.year-label {
  position: absolute;
  transform: translateX(-50%);
  font-family: var(--font-mono), 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--color-body, #4A4238);
  cursor: pointer;
  user-select: none;
  transition: color 0.15s ease;
}

.year-label:hover {
  color: var(--color-forest-600, #4A6741);
}

.year-label--active {
  color: var(--color-forest-700, #3A5233);
  font-weight: 600;
}

:global(.dark) .year-label {
  color: rgba(247, 243, 232, 0.7); /* Cream with opacity */
}

:global(.dark) .year-label:hover {
  color: var(--color-forest-300, #B5C9AF);
}

:global(.dark) .year-label--active {
  color: var(--color-forest-300, #B5C9AF);
  font-weight: 600;
}
</style>

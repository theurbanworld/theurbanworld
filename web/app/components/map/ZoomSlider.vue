<template>
  <div
    data-testid="zoom-slider-panel"
    class="fixed z-100 flex flex-col items-center gap-2 p-3 rounded-xl shadow-lg bg-parchment/95 dark:bg-espresso/95 backdrop-blur-sm
           right-64 top-20
           max-sm:right-2 max-sm:top-auto max-sm:bottom-4"
  >
    <!-- Scale label -->
    <span
      data-testid="scale-label"
      class="text-xs text-body/70 dark:text-cream/70"
    >
      Scale
    </span>

    <!-- Current level name -->
    <span
      data-testid="current-level-name"
      class="text-sm font-medium text-forest-700 dark:text-forest-300"
    >
      {{ currentLevelName }}
    </span>

    <!-- Level icons (vertical, Building at top to Metropolitan at bottom) -->
    <div class="flex flex-col gap-1 my-2">
      <UTooltip
        v-for="level in reversedLevels"
        :key="level.name"
        :text="level.name"
        :popper="{ placement: 'left' }"
      >
        <button
          :data-testid="`level-button-${level.name.toLowerCase()}`"
          :class="[
            'w-10 h-10 flex items-center justify-center rounded-lg transition-colors',
            'hover:bg-forest-100 dark:hover:bg-forest-900/50',
            currentLevelName === level.name
              ? 'bg-forest-200 dark:bg-forest-800 text-forest-700 dark:text-forest-300'
              : 'text-body/70 dark:text-cream/70'
          ]"
          :aria-label="`Zoom to ${level.name} level`"
          @click="snapToLevel(level.name)"
        >
          <UIcon
            :name="level.icon"
            class="w-5 h-5"
          />
        </button>
      </UTooltip>
    </div>

    <!-- Vertical Zoom Slider -->
    <div class="h-32 flex items-center">
      <USlider
        v-model="sliderValue"
        :min="MIN_ZOOM"
        :max="MAX_ZOOM"
        :step="0.5"
        orientation="vertical"
        data-testid="zoom-slider"
        class="zoom-slider h-full"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ZoomSlider - Vertical zoom control with named scale levels
 *
 * Displays a vertical slider for map zoom control with clickable
 * level icons for snap-to-level navigation. Bidirectionally synced
 * with the map zoom via useViewState.
 * On mobile, repositions to bottom-right corner.
 */

import { useViewState } from '../../composables/useViewState'
import { useZoomLevel, type ZoomLevelName } from '../../composables/useZoomLevel'

// Zoom range constants
const MIN_ZOOM = 0
const MAX_ZOOM = 18

// Composables
const { viewState, setZoom } = useViewState()
const { ZOOM_LEVELS, getCenterZoomForLevel, currentLevelName } = useZoomLevel()

// Reverse levels for display (Building at top, Metropolitan at bottom)
const reversedLevels = computed(() => [...ZOOM_LEVELS].reverse())

// Two-way binding for slider
const sliderValue = computed({
  get: () => viewState.value.zoom,
  set: (value: number) => {
    setZoom(value)
  }
})

/**
 * Snap to a specific zoom level by name
 */
function snapToLevel(levelName: ZoomLevelName) {
  const centerZoom = getCenterZoomForLevel(levelName)
  setZoom(centerZoom)
}
</script>

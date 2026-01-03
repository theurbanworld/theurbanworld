<template>
  <div
    data-testid="zoom-slider-panel"
    class="absolute z-100 p-3 rounded-xl shadow-lg bg-parchment/95 dark:bg-espresso/95 backdrop-blur-sm
           right-4 bottom-4 w-56
           max-sm:right-2 max-sm:bottom-2 max-sm:w-auto"
  >
    <!-- Scale label -->
    <span
      data-testid="scale-label"
      class="block text-xs text-body/70 dark:text-cream/70 mb-2"
    >
      Scale
    </span>

    <!-- Slider + Icons row -->
    <div class="flex flex-row gap-3">
      <!-- Vertical Zoom Slider (left side) -->
      <div class="h-52 flex items-center">
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

      <!-- Level icons with labels (right side, Building at top to Metropolitan at bottom) -->
      <div class="flex-1 flex flex-col justify-between h-52">
        <button
          v-for="level in reversedLevels"
          :key="level.name"
          :data-testid="`level-button-${level.name.toLowerCase()}`"
          :class="[
            'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors w-full',
            'hover:bg-forest-100 dark:hover:bg-forest-900/50',
            currentLevelName === level.name
              ? 'bg-forest-200 dark:bg-forest-800 text-forest-700 dark:text-forest-300 font-medium'
              : 'text-body/60 dark:text-cream/60'
          ]"
          :aria-label="`Zoom to ${level.name} level`"
          @click="snapToLevel(level.name)"
        >
          <UIcon
            :name="level.icon"
            class="w-5 h-5 shrink-0"
          />
          <span class="text-sm max-sm:hidden">{{ level.name }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ZoomSlider - Vertical zoom control with named scale levels
 *
 * Displays a vertical slider for map zoom control with clickable
 * level icons and labels for snap-to-level navigation. Positioned
 * at bottom-right corner, matching GlobalContextPanel width.
 * On mobile, labels are hidden but icons remain visible.
 */

import { useViewState } from '../../composables/useViewState'
import { useZoomLevel, type ZoomLevelName } from '../../composables/useZoomLevel'

// Zoom range constants
const MIN_ZOOM = 0
const MAX_ZOOM = 18

// Composables
const { viewState, setZoom, setZoomAnimated } = useViewState()
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
 * Snap to a specific zoom level by name with smooth animation
 */
function snapToLevel(levelName: ZoomLevelName) {
  const centerZoom = getCenterZoomForLevel(levelName)
  setZoomAnimated(centerZoom)
}
</script>

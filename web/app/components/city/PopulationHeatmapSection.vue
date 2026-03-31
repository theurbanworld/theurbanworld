<script setup lang="ts">
/**
 * PopulationHeatmapSection - Toggle to show per-cell population on the map
 *
 * Displays a "Show on map" toggle and a compact legend showing
 * the logarithmic sepia color scale. Only rendered for H3 datasets.
 */

import { getGradientColors, getPopulationRangeLabel } from '~/utils/colorScale'

const props = defineProps<{
  cityId: string
}>()

const { isPopulationLayerActive, isLoadingH3, setPopulationLayerActive } = usePopulationHighlight()
const { isRadialLayerActive, setRadialLayerActive } = useRadialHighlight()

function toggleMapLayer() {
  const next = !isPopulationLayerActive.value
  // Deactivate radial layer when activating population layer (they overlap)
  if (next && isRadialLayerActive.value) {
    setRadialLayerActive(false)
  }
  setPopulationLayerActive(next)
}

// Deactivate when component unmounts
onUnmounted(() => {
  setPopulationLayerActive(false)
})

// Deactivate when city changes
watch(() => props.cityId, () => {
  setPopulationLayerActive(false)
})

// Dark mode detection for correct legend gradient direction
const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

// Legend colors
const legendColors = computed(() => {
  return getGradientColors(isDark.value).map((rgba, i) => ({
    color: `rgb(${rgba[0]}, ${rgba[1]}, ${rgba[2]})`,
    label: getPopulationRangeLabel(i)
  }))
})
</script>

<template>
  <div class="border-t border-border/30 dark:border-border/20 pt-4">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-1.5">
        <h2 class="text-sm font-medium text-ink-700 dark:text-ink-300">
          Population
        </h2>
      </div>
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs cursor-pointer
               transition-colors"
        :class="isPopulationLayerActive
          ? 'bg-ink-600 text-white dark:bg-ink-500'
          : 'text-body/60 dark:text-cream/60 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
        :disabled="isLoadingH3"
        @click="toggleMapLayer"
      >
        <UIcon
          :name="isLoadingH3 ? 'i-lucide-loader-2' : 'i-lucide-map'"
          :class="['w-3.5 h-3.5', isLoadingH3 && 'animate-spin']"
        />
        <span>{{ isLoadingH3 ? 'Loading...' : isPopulationLayerActive ? 'On map' : 'Show on map' }}</span>
      </button>
    </div>

    <!-- Compact legend -->
    <div v-if="isPopulationLayerActive" class="flex items-center gap-1">
      <span class="text-[10px] text-body/50 dark:text-cream/50 shrink-0">Low</span>
      <div class="flex flex-1 h-2 rounded-sm overflow-hidden">
        <div
          v-for="(stop, i) in legendColors"
          :key="i"
          class="flex-1"
          :style="{ backgroundColor: stop.color }"
          :title="stop.label"
        />
      </div>
      <span class="text-[10px] text-body/50 dark:text-cream/50 shrink-0">High</span>
    </div>
  </div>
</template>

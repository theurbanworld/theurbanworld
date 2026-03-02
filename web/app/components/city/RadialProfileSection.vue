<script setup lang="ts">
/**
 * RadialProfileSection - Radial density profile chart with map layer toggle
 *
 * Always shows the chart. A toggle activates the DeckGL H3 radial
 * layer on the map to visualize ring distances.
 */

const props = defineProps<{
  cityId: string
}>()

const { isRadialLayerActive, setRadialLayerActive } = useRadialHighlight()

function toggleMapLayer() {
  setRadialLayerActive(!isRadialLayerActive.value)
}

// Deactivate layer when component unmounts
onUnmounted(() => {
  setRadialLayerActive(false)
})

// Deactivate when city changes
watch(() => props.cityId, () => {
  setRadialLayerActive(false)
})
</script>

<template>
  <div class="border-t border-border/30 dark:border-border/20 pt-4">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-medium text-forest-700 dark:text-forest-300">
        Radial Profile
      </h2>
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs cursor-pointer
               transition-colors"
        :class="isRadialLayerActive
          ? 'bg-forest-600 text-white dark:bg-forest-500'
          : 'text-body/60 dark:text-cream/60 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
        @click="toggleMapLayer"
      >
        <UIcon name="i-lucide-map" class="w-3.5 h-3.5" />
        <span>{{ isRadialLayerActive ? 'On map' : 'Show on map' }}</span>
      </button>
    </div>
    <RadialProfileChart :city-id="cityId" />
  </div>
</template>

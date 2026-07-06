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

const { open: openInfoModal } = useInfoModal()
const { isRadialLayerActive, setRadialLayerActive } = useRadialHighlight()
const { isPopulationLayerActive, setPopulationLayerActive } = usePopulationHighlight()

function toggleMapLayer() {
  const next = !isRadialLayerActive.value
  // Deactivate population layer when activating radial (they overlap)
  if (next && isPopulationLayerActive.value) {
    setPopulationLayerActive(false)
  }
  setRadialLayerActive(next)
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
  <div>
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-1.5">
        <h2 class="text-xs font-semibold uppercase tracking-wider text-body/60 dark:text-cream/60">
          Density Profile
        </h2>
        <button
          class="text-body/40 dark:text-cream/40 hover:text-ink-600 dark:hover:text-ink-400 transition-colors cursor-pointer"
          aria-label="About radial profiles"
          @click="openInfoModal('/methodology/bertaud-radial')"
        >
          <UIcon
            name="i-lucide-info"
            class="w-3.5 h-3.5"
          />
        </button>
      </div>
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs cursor-pointer
               transition-colors"
        :class="isRadialLayerActive
          ? 'bg-ink-600 text-white dark:bg-ink-500'
          : 'text-body/60 dark:text-cream/60 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
        @click="toggleMapLayer"
      >
        <UIcon
          name="i-lucide-map"
          class="w-3.5 h-3.5"
        />
        <span>{{ isRadialLayerActive ? 'On map' : 'Show on map' }}</span>
      </button>
    </div>
    <CityTypeBadge
      :city-id="cityId"
      class="mb-3"
    />
    <RadialProfileChart :city-id="cityId" />
  </div>
</template>

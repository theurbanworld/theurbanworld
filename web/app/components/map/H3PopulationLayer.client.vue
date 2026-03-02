<template>
  <!-- Renderless component - no DOM output -->
  <slot />
</template>

<script setup lang="ts">
/**
 * H3PopulationLayer - Renderless component for H3 hexagon visualization
 *
 * Uses the useH3Layer composable to create and manage the deck.gl layer.
 * Exposes the layer via defineExpose for parent components to integrate.
 * This is a renderless component that only manages state, not DOM elements.
 */

import type { Layer } from '@deck.gl/core'

const props = defineProps<{
  /** Whether dark mode is enabled */
  isDarkMode?: boolean
}>()

// Create the H3 layer using the composable
const isDarkModeRef = computed(() => props.isDarkMode ?? false)
const { layer, getVisibleHexagonCount } = useH3Layer({
  isDarkMode: isDarkModeRef
})

// Expose the layer and utilities for parent components
defineExpose({
  /** The current H3HexagonLayer instance */
  layer,
  /** Get count of visible hexagons */
  getVisibleHexagonCount
})

// Emit layer updates for parent to react to
const emit = defineEmits<{
  /** Emitted when the layer changes */
  'layer-update': [layer: Layer | null]
}>()

// Watch for layer changes and emit update
watch(layer, (newLayer) => {
  emit('layer-update', newLayer)
}, { immediate: true })
</script>

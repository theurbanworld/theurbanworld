<template>
  <div class="map-controls">
    <!-- Zoom in button -->
    <UButton
      icon="i-lucide-plus"
      color="neutral"
      variant="solid"
      size="lg"
      class="zoom-button"
      aria-label="Zoom in"
      @click="zoomIn"
    />

    <!-- Zoom out button -->
    <UButton
      icon="i-lucide-minus"
      color="neutral"
      variant="solid"
      size="lg"
      class="zoom-button"
      aria-label="Zoom out"
      @click="zoomOut"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * MapControls - Zoom control buttons for the map
 *
 * Position: fixed bottom-right, 16px from edges
 * Provides zoom in (+) and zoom out (-) buttons
 * Styled with forest green accent colors
 * No compass control (north always up per spec)
 */

// Emit events for parent to handle
const emit = defineEmits<{
  'zoom-in': []
  'zoom-out': []
}>()

/**
 * Zoom in handler
 */
function zoomIn() {
  emit('zoom-in')
}

/**
 * Zoom out handler
 */
function zoomOut() {
  emit('zoom-out')
}

// Expose methods for external access
defineExpose({
  zoomIn,
  zoomOut
})
</script>

<style scoped>
.map-controls {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Custom styling for zoom buttons */
.zoom-button {
  width: 44px;
  height: 44px;
  background-color: var(--color-forest-600, #4A6741) !important;
  color: var(--color-density-1, #F7F3E8) !important;
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: background-color 0.15s ease, transform 0.15s ease;
}

.zoom-button:hover {
  background-color: var(--color-forest-700, #3A5233) !important;
  transform: scale(1.05);
}

.zoom-button:active {
  transform: scale(0.98);
}

.zoom-button:focus-visible {
  outline: 2px solid var(--color-forest-400, #8FAD85);
  outline-offset: 2px;
}

/* Dark mode styles */
:global(.dark) .zoom-button {
  background-color: var(--color-forest-500, #6A8F5E) !important;
  color: var(--color-espresso, #3D352C) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

:global(.dark) .zoom-button:hover {
  background-color: var(--color-forest-400, #8FAD85) !important;
}

:global(.dark) .zoom-button:focus-visible {
  outline-color: var(--color-forest-300, #B5C9AF);
}
</style>

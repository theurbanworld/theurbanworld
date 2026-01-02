<script setup lang="ts">
/**
 * Main application page
 *
 * Renders the full-screen GlobalMap component with:
 * - Year slider overlay (bottom center)
 * - Map controls (bottom right)
 * - Dark mode toggle (top right)
 */

// Reference to GlobalMap component for accessing map instance
const globalMapRef = ref<{ zoomIn: () => void, zoomOut: () => void } | null>(null)

// Get dark mode state
const { isDarkMode, initializeDarkMode } = useDarkMode()

/**
 * Handle zoom in from MapControls
 */
function handleZoomIn() {
  globalMapRef.value?.zoomIn()
}

/**
 * Handle zoom out from MapControls
 */
function handleZoomOut() {
  globalMapRef.value?.zoomOut()
}

// Initialize dark mode on mount
onMounted(() => {
  initializeDarkMode()
})
</script>

<template>
  <div class="main-page">
    <!-- Global Map (full viewport) -->
    <ClientOnly>
      <GlobalMap
        ref="globalMapRef"
        :is-dark-mode="isDarkMode"
      />

      <YearSlider />

      <MapControls
        @zoom-in="handleZoomIn"
        @zoom-out="handleZoomOut"
      />

      <DarkModeToggle />
    </ClientOnly>
  </div>
</template>

<style scoped>
.main-page {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}
</style>

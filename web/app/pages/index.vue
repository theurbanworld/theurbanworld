<script setup lang="ts">
/**
 * Main application page
 *
 * Renders the full-screen GlobalMap component with:
 * - Global context panel (right side) - epoch controls and population data
 * - Zoom slider (right side) - vertical zoom control with named scale levels
 * - Dark mode toggle (top right header)
 */

// Get dark mode state
const { isDarkMode, initializeDarkMode } = useDarkMode()

// Initialize dark mode on mount
onMounted(() => {
  initializeDarkMode()
})
</script>

<template>
  <div class="w-full h-full relative overflow-hidden">
    <!-- Global Map (full viewport) -->
    <ClientOnly>
      <GlobalMap :is-dark-mode="isDarkMode" />

      <!-- Global Context Panel (epoch controls and population data) -->
      <GlobalContextPanel />

      <!-- Zoom Slider (scale level control) -->
      <ZoomSlider />
    </ClientOnly>
  </div>
</template>

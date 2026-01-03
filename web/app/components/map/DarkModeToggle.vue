<template>
  <UButton
    :icon="isDarkMode ? 'i-lucide-sun' : 'i-lucide-moon'"
    color="primary"
    variant="ghost"
    size="lg"
    class="cursor-pointer"
    :aria-label="isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="toggleDarkMode"
  />
</template>

<script setup lang="ts">
/**
 * DarkModeToggle - Toggle button for dark/light mode
 *
 * Position: fixed top-right, 16px from edges
 * Shows sun icon in dark mode (click to go light)
 * Shows moon icon in light mode (click to go dark)
 * Uses shared dark mode state via useDarkMode composable
 */

// Use shared dark mode state
const { isDarkMode, toggleDarkMode, initializeDarkMode } = useDarkMode()

// Initialize dark mode on mount (idempotent - only runs once)
onMounted(() => {
  initializeDarkMode()
})
</script>

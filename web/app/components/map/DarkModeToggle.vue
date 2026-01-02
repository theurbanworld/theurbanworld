<template>
  <UButton
    :icon="isDarkMode ? 'i-lucide-sun' : 'i-lucide-moon'"
    color="neutral"
    variant="ghost"
    size="lg"
    class="w-10 h-10 rounded-lg border-none transition-all duration-150 ease-out bg-forest-600 text-density-1 hover:bg-forest-700 hover:scale-105 active:scale-98 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-400 dark:bg-forest-500 dark:text-espresso dark:hover:bg-forest-400 dark:focus-visible:outline-forest-300"
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

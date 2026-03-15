<script setup lang="ts">
/**
 * DarkModeToggle - Toggle button for dark/light mode
 *
 * Shows sun icon in dark mode (click to go light)
 * Shows moon icon in light mode (click to go dark)
 * Uses shared dark mode state via useDarkMode composable
 */

const { isDarkMode, toggleDarkMode, initializeDarkMode } = useDarkMode()

onMounted(() => {
  initializeDarkMode()
})
</script>

<template>
  <UButton
    :icon="isDarkMode ? 'i-lucide-sun' : 'i-lucide-moon'"
    color="primary"
    variant="ghost"
    size="xs"
    class="cursor-pointer"
    :aria-label="isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="toggleDarkMode"
  />
</template>

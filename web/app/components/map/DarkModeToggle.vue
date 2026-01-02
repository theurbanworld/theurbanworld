<template>
  <UButton
    :icon="isDarkMode ? 'i-lucide-sun' : 'i-lucide-moon'"
    color="neutral"
    variant="solid"
    size="lg"
    class="dark-mode-toggle"
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

<style scoped>
.dark-mode-toggle {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
  width: 44px;
  height: 44px;
  background-color: var(--color-forest-600, #4A6741) !important;
  color: var(--color-density-1, #F7F3E8) !important;
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: background-color 0.15s ease, transform 0.15s ease;
}

.dark-mode-toggle:hover {
  background-color: var(--color-forest-700, #3A5233) !important;
  transform: scale(1.05);
}

.dark-mode-toggle:active {
  transform: scale(0.98);
}

.dark-mode-toggle:focus-visible {
  outline: 2px solid var(--color-forest-400, #8FAD85);
  outline-offset: 2px;
}

/* Dark mode styles */
:global(.dark) .dark-mode-toggle {
  background-color: var(--color-forest-500, #6A8F5E) !important;
  color: var(--color-espresso, #3D352C) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

:global(.dark) .dark-mode-toggle:hover {
  background-color: var(--color-forest-400, #8FAD85) !important;
}

:global(.dark) .dark-mode-toggle:focus-visible {
  outline-color: var(--color-forest-300, #B5C9AF);
}
</style>

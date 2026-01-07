<script setup lang="ts">
/**
 * Home page (global view)
 *
 * Route: /
 *
 * Clears city selection when navigating to this route.
 * All map components are rendered in app.vue.
 */

// Get city selection state
const { clearSelection } = useCitySelection()

// Clear city selection on mount (navigating to global view)
onMounted(() => {
  clearSelection()
})
</script>

<template>
  <!-- Route-specific content rendered here if needed -->
  <div />
</template>

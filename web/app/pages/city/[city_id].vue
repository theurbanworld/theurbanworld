<script setup lang="ts">
/**
 * City view page
 *
 * Displays the city info panel sidebar when a city is selected.
 * Syncs route params with city selection state.
 *
 * Route: /city/[city_id]
 */

// Get route params
const route = useRoute()

// Get city selection state
const { selectCity, clearSelection } = useCitySelection()

// Get dark mode state
const { isDarkMode, initializeDarkMode } = useDarkMode()

// Extract city_id from route params
const cityId = computed(() => {
  const id = route.params.city_id
  return Array.isArray(id) ? id[0] : id
})

// Sync route param to city selection state
watchEffect(() => {
  if (cityId.value) {
    selectCity(cityId.value)
  }
})

// Initialize dark mode on mount
onMounted(() => {
  initializeDarkMode()
})

// Clear selection when unmounting (navigating away)
onUnmounted(() => {
  clearSelection()
})

// Handle sidebar close - navigate back to global view
function handleSidebarClose() {
  navigateTo('/')
}
</script>

<template>
  <div class="w-full h-full relative overflow-hidden">
    <!-- Global Map (full viewport) -->
    <ClientOnly>
      <GlobalMap :is-dark-mode="isDarkMode" />

      <!-- City Info Panel Sidebar -->
      <AppSidebar :open="true" @close="handleSidebarClose">
        <CityInfoPanel v-if="cityId" :city-id="cityId" />
      </AppSidebar>

      <!-- Global Context Panel (epoch controls and population data) -->
      <GlobalContextPanel />

      <!-- Zoom Slider (scale level control) -->
      <ZoomSlider />
    </ClientOnly>
  </div>
</template>

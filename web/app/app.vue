<script setup lang="ts">
/**
 * Root app layout
 *
 * Contains persistent components that stay mounted across route changes:
 * - GlobalMap (full viewport map)
 * - AppSidebar with CityInfoPanel (shown when city selected)
 * - GlobalContextPanel (epoch controls and population data)
 * - ZoomSlider (scale level control)
 */

// Get dark mode state
const { isDarkMode, initializeDarkMode } = useDarkMode()

// Get city selection state
const { selectedCityId, clearSelection } = useCitySelection()

// Initialize dark mode on mount
onMounted(() => {
  initializeDarkMode()
})

// Handle sidebar close - navigate back to global view
function handleSidebarClose() {
  clearSelection()
  navigateTo('/')
}
</script>

<template>
  <UApp>
    <div class="flex flex-col h-screen overflow-hidden">
      <AppHeader />

      <div class="flex flex-1 min-h-0 overflow-hidden">
        <!-- City Info Panel Sidebar (pushes map when open) -->
        <AppSidebar :open="!!selectedCityId" @close="handleSidebarClose">
          <CityInfoPanel v-if="selectedCityId" :city-id="selectedCityId" @close="handleSidebarClose" />
        </AppSidebar>

        <UMain class="flex-1 !min-h-0 relative overflow-hidden">
          <!-- Persistent map and overlays -->
          <ClientOnly>
            <GlobalMap :is-dark-mode="isDarkMode" />

            <!-- Global Context Panel (epoch controls and population data) -->
            <GlobalContextPanel />

            <!-- Zoom Slider (scale level control) -->
            <ZoomSlider />
          </ClientOnly>

          <!-- Route-specific content -->
          <NuxtPage />
        </UMain>
      </div>

      <AppFooter />
    </div>
  </UApp>
</template>

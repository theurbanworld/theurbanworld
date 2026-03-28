<script setup lang="ts">
/**
 * Default layout — explore mode (map + sidebar)
 *
 * Contains the search strip, sidebar, map, and overlay panels.
 * Extracted from app.vue so content pages can use a different layout.
 */

// Get city selection state
const { selectedCityId, clearSelection } = useCitySelection()

// Get dark mode state for map
const { isDarkMode } = useDarkMode()

// Route detection for sidebar content
const route = useRoute()
const isRankingsRoute = computed(() => route.path === '/')

// Mobile sidebar visibility
const mobileSidebarOpen = computed(() => !!selectedCityId.value || isRankingsRoute.value)

// Navigate to rankings (home)
function goToRankings() {
  clearSelection()
  navigateTo('/')
}

// Handle city info close - back to global view
function handleCityClose() {
  clearSelection()
  navigateTo('/')
}
</script>

<template>
  <!-- Search strip: toggle left, search centered on page -->
  <div class="relative bg-parchment border-b border-forest-200/40 dark:border-forest-800/40">
    <!-- Cities toggle — sidebar width, left-aligned with border -->
    <div class="absolute inset-y-0 left-0 w-96 flex items-center px-4 border-r border-forest-200/40 dark:border-forest-800/40">
      <UButton
        variant="ghost"
        color="neutral"
        size="sm"
        class="cursor-pointer"
        :active="isRankingsRoute"
        active-variant="subtle"
        @click="goToRankings"
      >
        Cities
      </UButton>
    </div>
    <!-- Search — centered on full page width -->
    <div class="flex justify-center px-5 py-2.5">
      <CitySearch class="w-full max-w-sm" />
    </div>
  </div>

  <div class="flex flex-1 min-h-0 overflow-hidden">
    <!-- Sidebar — always visible on desktop, overlay on mobile -->
    <AppSidebar :open="mobileSidebarOpen">
      <template v-if="isRankingsRoute" #header>
        <RankingFilters />
      </template>
      <CityRankings v-if="isRankingsRoute" />
      <div v-else-if="selectedCityId" class="p-5">
        <CityInfoPanel :city-id="selectedCityId" @close="handleCityClose" />
      </div>
    </AppSidebar>

    <UMain class="flex-1 !min-h-0 relative overflow-hidden">
      <!-- Persistent map and overlays -->
      <GlobalMap :is-dark-mode="isDarkMode" />

      <!-- Global Context Panel (epoch controls and population data) -->
      <GlobalContextPanel />

      <!-- Zoom Slider (scale level control) — hidden, replaced by MapLibre NavigationControl -->
      <!-- <ZoomSlider /> -->

      <!-- Route-specific content -->
      <slot />
    </UMain>
  </div>
</template>

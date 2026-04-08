<script setup lang="ts">
/**
 * Default layout — explore mode (map + sidebar)
 *
 * Desktop: full-width controls strip, then sidebar (left) + map (right).
 * Mobile: map-first with bottom drawer for sidebar content.
 */

// Get city selection state
const { selectedCityId, clearSelection } = useCitySelection()

// Get dark mode state for map
const { isDarkMode } = useDarkMode()

// Route detection for sidebar content
const route = useRoute()
const isRankingsRoute = computed(() => route.path === '/')

// Mobile sidebar
const { open: openMobileSidebar } = useMobileSidebar()

// Auto-open mobile drawer when a city is selected
watch(selectedCityId, (id) => {
  if (id) openMobileSidebar()
})

// Handle city info close - back to global view
function handleCityClose() {
  clearSelection()
  navigateTo('/')
}
</script>

<template>
  <div class="flex flex-col flex-1 min-h-0 overflow-hidden">
    <!-- Full-width controls strip: epoch left, dataset right -->
    <div class="flex items-center justify-between gap-3 px-4 py-2 bg-parchment border-b border-ink-200/40 dark:border-ink-800/40">
      <EpochStrip />
      <div class="flex items-center gap-3">
        <DatasetPicker />
        <GlobalPopulationDropdown />
      </div>
    </div>

    <!-- Sidebar + Map row -->
    <div class="flex flex-1 min-h-0 overflow-hidden">
      <AppSidebar>
        <template #header>
          <StatToggle v-if="isRankingsRoute" />
          <RankingFilters v-if="isRankingsRoute" />
        </template>
        <CityRankings v-if="isRankingsRoute" />
        <div v-else-if="selectedCityId" class="p-5">
          <CityInfoPanel :city-id="selectedCityId" @close="handleCityClose" />
        </div>
      </AppSidebar>

      <div class="flex-1 flex flex-col min-h-0">
        <UMain class="flex-1 !min-h-0 relative overflow-hidden">
          <GlobalMap :is-dark-mode="isDarkMode" />
          <GlobalPopulationPanel />

          <!-- Mobile floating pill to open sidebar drawer -->
          <button
            class="sm:hidden absolute bottom-6 left-1/2 -translate-x-1/2 z-50
                   bg-parchment/95 dark:bg-ink-950/95 backdrop-blur-sm
                   rounded-full px-4 py-2.5 shadow-lg
                   flex items-center gap-2 text-sm font-medium
                   text-ink-700 dark:text-ink-300
                   active:scale-95 transition-transform cursor-pointer"
            @click="openMobileSidebar"
          >
            <UIcon name="i-lucide-bar-chart-3" class="w-4 h-4" />
            <span v-if="isRankingsRoute">Rankings</span>
            <span v-else-if="selectedCityId">City Info</span>
            <span v-else>Rankings</span>
          </button>

          <slot />
        </UMain>
      </div>
    </div>
  </div>
</template>

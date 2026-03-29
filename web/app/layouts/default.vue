<script setup lang="ts">
/**
 * Default layout — explore mode (map + sidebar)
 *
 * Desktop: sidebar (left) + controls strip + map (right).
 * Mobile: map-first with bottom drawer for sidebar content.
 */

// Get city selection state
const { selectedCityId, clearSelection } = useCitySelection()

// Get dark mode state for map
const { isDarkMode } = useDarkMode()

// Epoch year for compact display
const { selectedYear } = useSelectedYear()

// Eyebrow panel toggle
const { isExpanded, toggle: toggleEyebrow } = useEyebrowPanel()

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
      <!-- Controls strip — dataset picker and epoch toggle -->
      <div class="flex items-center justify-end gap-3 px-4 py-2 bg-parchment border-b border-ink-200/40 dark:border-ink-800/40">
        <DatasetPicker />
        <button
          data-testid="eyebrow-toggle"
          class="flex flex-col items-start py-1 px-2 -mr-2 rounded-md
                 hover:bg-ink-100/50 dark:hover:bg-ink-900/30
                 transition-colors cursor-pointer"
          :title="isExpanded ? 'Hide global stats' : 'Show global stats'"
          @click="toggleEyebrow"
        >
          <span class="text-[10px] leading-tight text-body/50 dark:text-cream/50">Epoch</span>
          <span class="flex items-center gap-1">
            <span class="font-mono text-sm font-bold leading-tight text-ink-700 dark:text-ink-300 tracking-wide">
              {{ selectedYear }}
            </span>
            <UIcon
              :name="isExpanded ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
              class="w-3.5 h-3.5 block text-body/50 dark:text-cream/50"
            />
          </span>
        </button>
      </div>

      <UMain class="flex-1 !min-h-0 relative overflow-hidden">
        <GlobalMap :is-dark-mode="isDarkMode" />
        <EyebrowPanel />

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
</template>

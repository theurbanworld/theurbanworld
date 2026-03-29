<script setup lang="ts">
/**
 * Default layout — explore mode (map + sidebar)
 *
 * Full-height sidebar (left) with search strip + map (right).
 * StatToggle and RankingFilters render in the sidebar header
 * only on the rankings route.
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

// Mobile sidebar visibility
const mobileSidebarOpen = computed(() => !!selectedCityId.value || isRankingsRoute.value)

// Handle city info close - back to global view
function handleCityClose() {
  clearSelection()
  navigateTo('/')
}
</script>

<template>
  <div class="flex flex-1 min-h-0 overflow-hidden">
    <AppSidebar :open="mobileSidebarOpen">
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
      <!-- Search strip — search bar offset left by half sidebar width to center on viewport -->
      <div class="grid grid-cols-[1fr_auto_1fr] items-center bg-parchment border-b border-ink-200/40 dark:border-ink-800/40">
        <div />
        <div class="-translate-x-48 px-5 py-2.5">
          <CitySearch class="w-full max-w-xs" />
        </div>
        <div class="flex items-center justify-end gap-3 px-4">
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
      </div>

      <UMain class="flex-1 !min-h-0 relative overflow-hidden">
        <GlobalMap :is-dark-mode="isDarkMode" />
        <EyebrowPanel />
        <slot />
      </UMain>
    </div>
  </div>
</template>

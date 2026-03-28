<script setup lang="ts">
/**
 * Default layout — explore mode (map + sidebar)
 *
 * Full-width search strip sits above the sidebar+map flex row.
 * The strip uses a 3-column flex: stat buttons (left, sidebar-width),
 * search (center), dataset+epoch (right).
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
  <!-- Full-width search strip -->
  <div class="flex items-stretch bg-parchment">
    <!-- Stat toggle — same width as sidebar, full-height right border -->
    <StatToggle />
    <!-- Search — centered in remaining space -->
    <div class="flex-1 flex justify-center px-5 py-2.5 border-b border-ink-200/40 dark:border-ink-800/40">
      <CitySearch class="w-full max-w-sm" />
    </div>
    <!-- Dataset + epoch + eyebrow toggle — right -->
    <div class="flex items-center justify-end gap-3 px-4 shrink-0 border-b border-ink-200/40 dark:border-ink-800/40">
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

  <!-- 2-column layout: sidebar | map -->
  <div class="flex flex-1 min-h-0 overflow-hidden">
    <AppSidebar :open="mobileSidebarOpen">
      <template #header>
        <RankingFilters v-if="isRankingsRoute" />
      </template>
      <CityRankings v-if="isRankingsRoute" />
      <div v-else-if="selectedCityId" class="p-5">
        <CityInfoPanel :city-id="selectedCityId" @close="handleCityClose" />
      </div>
    </AppSidebar>

    <UMain class="flex-1 !min-h-0 relative overflow-hidden">
      <GlobalMap :is-dark-mode="isDarkMode" />
      <EyebrowPanel />
      <slot />
    </UMain>
  </div>
</template>

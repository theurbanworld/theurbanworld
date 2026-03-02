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

useHead({
  title: 'The Urban World — an observatory of urban complexity',
  link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]
})

useSeoMeta({
  description: 'The Urban World tells the story of global urbanization through data, making visible the shape, density, and growth of cities over time.',
  ogTitle: 'The Urban World — an observatory of urban complexity',
  ogDescription: 'The Urban World tells the story of global urbanization through data, making visible the shape, density, and growth of cities over time.'
})

defineOgImage({
  component: 'Default'
})

// Get dark mode state
const { isDarkMode, initializeDarkMode } = useDarkMode()

// Get city selection state
const { selectedCityId, clearSelection } = useCitySelection()

// Route detection for sidebar content
const route = useRoute()
const isRankingsRoute = computed(() => route.path === '/rankings')

// Mobile sidebar visibility
const mobileSidebarOpen = computed(() => !!selectedCityId.value || isRankingsRoute.value)

// Initialize dark mode on mount
onMounted(() => {
  initializeDarkMode()
})

// Toggle rankings view
function toggleRankings() {
  if (isRankingsRoute.value) {
    clearSelection()
    navigateTo('/')
  } else {
    clearSelection()
    navigateTo('/rankings')
  }
}

// Handle city info close - back to global view
function handleCityClose() {
  clearSelection()
  navigateTo('/')
}
</script>

<template>
  <UApp>
    <div class="flex flex-col h-screen overflow-hidden">
      <AppHeader />

      <!-- Search strip: sidebar-width toggle on left, centered search on right -->
      <div class="flex items-center bg-parchment border-b border-forest-200/40 dark:border-forest-800/40">
        <!-- Cities toggle — sidebar width -->
        <div class="w-80 shrink-0 px-4 py-2.5 border-r border-forest-200/40 dark:border-forest-800/40">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer"
            :class="isRankingsRoute
              ? 'bg-forest-700 text-white dark:bg-forest-400 dark:text-forest-950'
              : 'text-body/60 dark:text-cream/60 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
            @click="toggleRankings"
          >
            <UIcon name="i-lucide-bar-chart-horizontal" class="w-4 h-4" />
            Cities
          </button>
        </div>
        <!-- Search — centered in remaining space -->
        <div class="flex-1 flex justify-center px-5 py-2.5">
          <CitySearch class="w-full max-w-sm" />
        </div>
      </div>

      <div class="flex flex-1 min-h-0 overflow-hidden">
        <!-- Sidebar — always visible on desktop, overlay on mobile -->
        <AppSidebar :open="mobileSidebarOpen">
          <CityRankings v-if="isRankingsRoute" />
          <CityInfoPanel v-else-if="selectedCityId" :city-id="selectedCityId" @close="handleCityClose" />
        </AppSidebar>

        <UMain class="flex-1 !min-h-0 relative overflow-hidden">
          <!-- Persistent map and overlays -->
          <GlobalMap :is-dark-mode="isDarkMode" />

          <!-- Global Context Panel (epoch controls and population data) -->
          <GlobalContextPanel />

          <!-- Zoom Slider (scale level control) -->
          <ZoomSlider />

          <!-- Route-specific content -->
          <NuxtPage />
        </UMain>
      </div>

      <AppFooter />
    </div>
  </UApp>
</template>

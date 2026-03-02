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
const sidebarOpen = computed(() => !!selectedCityId.value || isRankingsRoute.value)

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

      <div class="flex flex-1 min-h-0 overflow-hidden relative">
        <!-- Search notch — same width as sidebar, always visible -->
        <div class="absolute top-0 left-0 z-20 w-80 p-3 bg-parchment border-r border-b border-forest-200/40 dark:border-forest-800/40 rounded-br-lg">
          <CitySearch class="w-full" />
          <NuxtLink
            to="/rankings"
            class="mt-2 inline-flex items-center gap-1.5 text-xs transition-colors"
            :class="isRankingsRoute
              ? 'text-forest-700 dark:text-forest-300 font-medium'
              : 'text-body/60 dark:text-cream/60 hover:text-forest-700 dark:hover:text-forest-300'"
          >
            <UIcon name="i-lucide-bar-chart-horizontal" class="w-3.5 h-3.5" />
            Rankings
          </NuxtLink>
        </div>

        <!-- Sidebar (pushes map when open) -->
        <AppSidebar :open="sidebarOpen" @close="handleSidebarClose">
          <CityRankings v-if="isRankingsRoute" @close="handleSidebarClose" />
          <CityInfoPanel v-else-if="selectedCityId" :city-id="selectedCityId" @close="handleSidebarClose" />
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

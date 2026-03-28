<script setup lang="ts">
/**
 * Compare layout — dual-map comparison mode
 *
 * Contains the search strip, sidebar, two map containers (side-by-side
 * on desktop, A/B toggle on mobile), and the epoch controls.
 * Comparison content is rendered via the default slot.
 */

// Get dark mode state for maps
const { isDarkMode } = useDarkMode()

// Read comparison state directly (layout is parent of page, so inject won't work)
const { cityA, cityB, isValid } = useComparisonState()

// Mobile toggle state
const activeMapSide = ref<'A' | 'B'>('A')

// City names for mobile toggle labels
const { getCity } = useCitiesIndex()
const cityAName = computed(() => cityA.value ? getCity(cityA.value)?.name ?? 'City A' : 'City A')
const cityBName = computed(() => cityB.value ? getCity(cityB.value)?.name ?? 'City B' : 'City B')

// Navigate to rankings (home)
function goToRankings() {
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
    <!-- Sidebar — comparison content via slot -->
    <AppSidebar :open="true">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-body dark:text-cream">Comparison</span>
          <UButton
            variant="ghost"
            color="neutral"
            size="xs"
            icon="i-lucide-x"
            class="cursor-pointer"
            aria-label="Close comparison"
            @click="goToRankings"
          />
        </div>
      </template>
      <slot />
    </AppSidebar>

    <UMain class="flex-1 !min-h-0 relative overflow-hidden">
      <!-- Dual map area -->
      <div v-if="isValid && cityA && cityB" class="flex h-full">
        <!-- Desktop: two maps side by side -->
        <div class="hidden sm:flex w-full h-full">
          <div class="flex-1 h-full relative border-r border-forest-200/40 dark:border-forest-800/40">
            <ComparisonMap
              :city-id="cityA"
              map-id="A"
              :is-dark-mode="isDarkMode"
            />
          </div>
          <div class="flex-1 h-full relative">
            <ComparisonMap
              :city-id="cityB"
              map-id="B"
              :is-dark-mode="isDarkMode"
            />
          </div>
        </div>

        <!-- Mobile: single map with toggle -->
        <div class="sm:hidden w-full h-full relative">
          <ComparisonMap
            v-show="activeMapSide === 'A'"
            :city-id="cityA"
            map-id="A"
            :is-dark-mode="isDarkMode"
          />
          <ComparisonMap
            v-show="activeMapSide === 'B'"
            :city-id="cityB"
            map-id="B"
            :is-dark-mode="isDarkMode"
          />
          <!-- Mobile A/B toggle -->
          <div class="absolute top-3 left-1/2 -translate-x-1/2 z-50 flex rounded-lg overflow-hidden shadow-md bg-parchment/95 backdrop-blur-sm">
            <button
              class="px-3 py-1.5 text-xs font-medium transition-colors"
              :class="activeMapSide === 'A'
                ? 'bg-forest-700 text-white dark:bg-forest-500'
                : 'text-body/70 dark:text-cream/70 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
              @click="activeMapSide = 'A'"
            >
              {{ cityAName }}
            </button>
            <button
              class="px-3 py-1.5 text-xs font-medium transition-colors"
              :class="activeMapSide === 'B'
                ? 'bg-amber-700 text-white dark:bg-amber-500'
                : 'text-body/70 dark:text-cream/70 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
              @click="activeMapSide = 'B'"
            >
              {{ cityBName }}
            </button>
          </div>
        </div>
      </div>

      <!-- Loading state -->
      <div v-else class="flex items-center justify-center h-full">
        <p class="text-body/50 dark:text-cream/50 text-sm">Loading comparison...</p>
      </div>

      <!-- Epoch controls — positioned between the two maps on desktop -->
      <GlobalContextPanel />
    </UMain>
  </div>
</template>

<script setup lang="ts">
/**
 * CityInfoPanel - Displays city statistics in the sidebar
 *
 * Shows city name, country, and key statistics (population, density, area)
 * arranged in a 2x2 grid. All data is reactive to epoch changes via useCityStats.
 */

import { useCityStats } from '../../composables/useCityStats'
import { useDataset } from '../../composables/useDataset'
import { getGradientColors, getPopulationRangeLabel } from '~/utils/colorScale'

interface Props {
  /** City ID to display statistics for */
  cityId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
}>()

// Create a computed ref for the city ID to ensure reactivity
const cityIdRef = computed(() => props.cityId)

// Compare modal state
const compareModalOpen = ref(false)

// Dataset feature gating
const { hasFeatureComputed } = useDataset()
const showRadialProfiles = hasFeatureComputed('radialProfiles')
const showH3Overlay = hasFeatureComputed('h3Overlay')
const showClimate = hasFeatureComputed('climate')

// Population heatmap "Show on map" toggle (H3 datasets only)
const { isPopulationLayerActive, isLoadingH3, setPopulationLayerActive } = usePopulationHighlight()
const { isRadialLayerActive, setRadialLayerActive } = useRadialHighlight()

function togglePopulationLayer() {
  const next = !isPopulationLayerActive.value
  // Deactivate radial layer when activating population layer (they overlap)
  if (next && isRadialLayerActive.value) {
    setRadialLayerActive(false)
  }
  setPopulationLayerActive(next)
}

// Deactivate when the panel unmounts or the city changes
onUnmounted(() => {
  setPopulationLayerActive(false)
})
watch(() => props.cityId, () => {
  setPopulationLayerActive(false)
})

// Dark mode detection for correct legend gradient direction
const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

// Population heatmap legend colors
const legendColors = computed(() => {
  return getGradientColors(isDark.value).map((rgba, i) => ({
    color: `rgb(${rgba[0]}, ${rgba[1]}, ${rgba[2]})`,
    label: getPopulationRangeLabel(i)
  }))
})

// Get reactive city statistics
const {
  isLoading,
  error,
  cityName,
  countryName,
  populationRaw,
  populationHumanized,
  populationTrendPrevious,
  populationTrendNext,
  density,
  densityFormatted,
  densityTrendPrevious,
  densityTrendNext,
  area,
  areaFormatted,
  birthYear,
  deathYear,
  isPreCity,
  isActiveCity,
  cityStateMessage
} = useCityStats(cityIdRef)
</script>

<template>
  <div
    data-testid="city-info-panel"
    class="flex flex-col"
  >
    <!-- Loading skeleton -->
    <div
      v-if="isLoading"
      class="animate-pulse"
    >
      <div class="h-8 bg-muted rounded w-3/4 mb-2" />
      <div class="h-4 bg-muted rounded w-1/2 mb-6" />
      <div class="grid grid-cols-2 gap-4">
        <div class="h-20 bg-muted rounded" />
        <div class="h-20 bg-muted rounded" />
        <div class="h-20 bg-muted rounded" />
        <div class="h-20 bg-muted rounded" />
      </div>
    </div>

    <!-- Error state -->
    <div
      v-else-if="error"
      class="text-red-500 dark:text-red-400"
    >
      <p class="font-medium">
        Failed to load city data
      </p>
      <p class="text-sm mt-1">
        {{ error.message }}
      </p>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- City Header -->
      <header class="mb-6">
        <div class="flex items-start justify-between gap-2">
          <h1
            data-testid="city-name"
            class="text-4xl font-bold font-heading text-ink-700 dark:text-ink-300"
          >
            {{ cityName }}
          </h1>
          <CloseButton
            data-testid="sidebar-close-button"
            class="mt-1.5"
            aria-label="Close sidebar"
            @click="emit('close')"
          />
        </div>
        <p
          data-testid="country-name"
          class="text-sm text-body/70 dark:text-cream/70 mt-1"
        >
          {{ countryName }}
        </p>
      </header>

      <!-- Actions row (room for future city modes) -->
      <div class="flex items-center flex-wrap gap-1 mb-4 -mt-3">
        <button
          class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium cursor-pointer
                 text-body/60 dark:text-cream/60
                 hover:bg-ink-100/50 dark:hover:bg-ink-900/30
                 hover:text-ink-700 dark:hover:text-ink-300
                 transition-colors"
          @click="compareModalOpen = true"
        >
          <UIcon
            name="i-lucide-columns-2"
            class="w-3.5 h-3.5"
          />
          Compare to another city
        </button>
        <!-- future mode actions go here, same button pattern -->
      </div>

      <!-- Compare search modal -->
      <CompareSearchModal
        v-model:open="compareModalOpen"
        :current-city-id="cityId"
      />

      <!-- Pre/post-city state banner -->
      <div
        v-if="cityStateMessage"
        class="mb-4 px-3 py-2 rounded-md text-sm font-medium"
        :class="isPreCity
          ? 'bg-amber-100/60 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300'
          : 'bg-stone-100/60 text-stone-600 dark:bg-stone-800/30 dark:text-stone-400'"
      >
        {{ cityStateMessage }}
      </div>

      <!-- DataPoints -->
      <div
        data-testid="datapoint-grid"
        class="flex flex-col gap-6"
      >
        <div
          data-testid="population-datapoint"
          class="border-l-2 border-ink-400/60 dark:border-brass-500/50 pl-4"
        >
          <DataPoint
            id="city-population"
            label="Population"
            :value="populationHumanized"
            :raw-value="populationRaw"
            :trend-previous="isActiveCity ? populationTrendPrevious : null"
            :trend-next="isActiveCity ? populationTrendNext : null"
            source-label="Source: GHSL"
            content-path="/data/source-ghsl"
            toggle-label-a="over time"
            toggle-label-b="all cities"
            toggle-separator="vs"
          >
            <template
              v-if="showH3Overlay"
              #header-action
            >
              <button
                class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs cursor-pointer
                       transition-colors"
                :class="isPopulationLayerActive
                  ? 'bg-ink-600 text-white dark:bg-ink-500'
                  : 'text-body/60 dark:text-cream/60 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
                :disabled="isLoadingH3"
                @click="togglePopulationLayer"
              >
                <UIcon
                  :name="isLoadingH3 ? 'i-lucide-loader-2' : 'i-lucide-map'"
                  :class="['w-3.5 h-3.5', isLoadingH3 && 'animate-spin']"
                />
                <span>{{ isLoadingH3 ? 'Loading...' : isPopulationLayerActive ? 'On map' : 'Show on map' }}</span>
              </button>
            </template>
            <!-- Population heatmap legend, directly under the header (visible while layer is active) -->
            <template
              v-if="showH3Overlay && isPopulationLayerActive"
              #subheader
            >
              <div class="flex items-center gap-1 mt-1 mb-0.5">
                <span class="text-[10px] text-body/50 dark:text-cream/50 shrink-0">Low</span>
                <div class="flex flex-1 h-2 rounded-sm overflow-hidden">
                  <div
                    v-for="(stop, i) in legendColors"
                    :key="i"
                    class="flex-1"
                    :style="{ backgroundColor: stop.color }"
                    :title="stop.label"
                  />
                </div>
                <span class="text-[10px] text-body/50 dark:text-cream/50 shrink-0">High</span>
              </div>
            </template>
            <template #chart-a>
              <EpochSparkline
                :city-id="cityId"
                metric="population"
                :birth-year="birthYear ?? undefined"
                :death-year="deathYear ?? undefined"
              />
            </template>
            <template #chart-b>
              <DistributionStrip
                :city-id="cityId"
                metric="population"
              />
            </template>
          </DataPoint>
        </div>

        <div
          v-if="isActiveCity"
          data-testid="density-datapoint"
          class="border-l-2 border-ink-400/60 dark:border-brass-500/50 pl-4"
        >
          <DataPoint
            id="city-density"
            label="Density"
            :value="densityFormatted"
            :raw-value="density"
            :trend-previous="densityTrendPrevious"
            :trend-next="densityTrendNext"
            source-label="Source: GHSL"
            content-path="/data/source-ghsl"
            toggle-label-a="over time"
            toggle-label-b="all cities"
            toggle-separator="vs"
          >
            <template #chart-a>
              <EpochSparkline
                :city-id="cityId"
                metric="density_per_km2"
                :birth-year="birthYear ?? undefined"
                :death-year="deathYear ?? undefined"
              />
            </template>
            <template #chart-b>
              <DistributionStrip
                :city-id="cityId"
                metric="density_per_km2"
              />
            </template>
          </DataPoint>
        </div>

        <div
          v-if="isActiveCity"
          data-testid="area-datapoint"
          class="border-l-2 border-ink-400/60 dark:border-brass-500/50 pl-4"
        >
          <DataPoint
            id="city-area"
            label="Area"
            :value="areaFormatted"
            :raw-value="area"
            source-label="Source: GHSL"
            content-path="/data/source-ghsl"
            toggle-label-a="over time"
            toggle-label-b="all cities"
            toggle-separator="vs"
          >
            <template #chart-a>
              <EpochSparkline
                :city-id="cityId"
                metric="area_km2"
                :birth-year="birthYear ?? undefined"
                :death-year="deathYear ?? undefined"
              />
            </template>
            <template #chart-b>
              <DistributionStrip
                :city-id="cityId"
                metric="area_km2"
              />
            </template>
          </DataPoint>
        </div>

        <!-- Radial Profile Section (Urban World only) -->
        <RadialProfileSection
          v-if="showRadialProfiles"
          :city-id="cityId"
          class="border-l-2 border-ink-400/60 dark:border-brass-500/50 pl-4"
        />
      </div>

      <!-- Climate & Energy Section (per-city coverage gated inside) -->
      <ClimateEnergySection
        v-if="showClimate"
        :city-id="cityId"
        class="mt-4"
      />

      <!-- Media Resources (deferred — CityMediaSection component exists but content not yet populated) -->
    </template>
  </div>
</template>

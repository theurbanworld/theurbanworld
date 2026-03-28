<script setup lang="ts">
/**
 * CityInfoPanel - Displays city statistics in the sidebar
 *
 * Shows city name, country, and key statistics (population, density, area)
 * arranged in a 2x2 grid. All data is reactive to epoch changes via useCityStats.
 */

import { useCityStats } from '../../composables/useCityStats'

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
  isAvailable
} = useCityStats(cityIdRef)
</script>

<template>
  <div data-testid="city-info-panel" class="flex flex-col">
    <!-- Loading skeleton -->
    <div v-if="isLoading" class="animate-pulse">
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
    <div v-else-if="error" class="text-red-500 dark:text-red-400">
      <p class="font-medium">Failed to load city data</p>
      <p class="text-sm mt-1">{{ error.message }}</p>
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
          <button
            data-testid="sidebar-close-button"
            class="shrink-0 p-1 rounded-md cursor-pointer
                   text-body/50 dark:text-cream/50
                   hover:bg-ink-100/50 dark:hover:bg-ink-900/30
                   hover:text-ink-700 dark:hover:text-ink-300
                   transition-colors"
            aria-label="Close sidebar"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="w-4 h-4" />
          </button>
        </div>
        <p
          data-testid="country-name"
          class="text-sm text-body/70 dark:text-cream/70 mt-1"
        >
          {{ countryName }}
        </p>
      </header>

      <!-- DataPoints -->
      <div
        data-testid="datapoint-grid"
        class="flex flex-col gap-4"
      >
        <div data-testid="population-datapoint">
          <DataPoint
            id="city-population"
            label="Population"
            :value="populationHumanized"
            :raw-value="populationRaw"
            :trend-previous="populationTrendPrevious"
            :trend-next="populationTrendNext"
            source-label="Source: GHSL"
            content-path="/data/source-ghsl"
          >
            <EpochSparkline :city-id="cityId" metric="population" class="mt-1" />
          </DataPoint>
        </div>

        <div data-testid="density-datapoint">
          <DataPoint
            id="city-density"
            label="Density"
            :value="densityFormatted"
            :raw-value="density"
            :trend-previous="densityTrendPrevious"
            :trend-next="densityTrendNext"
            source-label="Source: GHSL"
            content-path="/data/source-ghsl"
          >
            <EpochSparkline :city-id="cityId" metric="density_per_km2" class="mt-1" />
          </DataPoint>
        </div>

        <div data-testid="area-datapoint">
          <DataPoint
            id="city-area"
            label="Area"
            :value="areaFormatted"
            :raw-value="area"
            source-label="Source: GHSL"
            content-path="/data/source-ghsl"
          >
            <EpochSparkline :city-id="cityId" metric="area_km2" class="mt-1" />
          </DataPoint>
        </div>
      </div>

      <!-- Radial Profile Section -->
      <RadialProfileSection :city-id="cityId" class="mt-4" />

      <!-- Media Resources -->
      <CityMediaSection :city-id="cityId" class="mt-4" />
    </template>
  </div>
</template>

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

// Create a computed ref for the city ID to ensure reactivity
const cityIdRef = computed(() => props.cityId)

// Get reactive city statistics
const {
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
    <!-- City Header -->
    <header class="mb-6">
      <h1
        data-testid="city-name"
        class="text-2xl font-bold text-forest-700 dark:text-forest-300"
      >
        {{ cityName }}
      </h1>
      <p
        data-testid="country-name"
        class="text-sm text-body/70 dark:text-cream/70 mt-1"
      >
        {{ countryName }}
      </p>
    </header>

    <!-- DataPoint 2x2 Grid -->
    <div
      data-testid="datapoint-grid"
      class="grid grid-cols-2 gap-4"
    >
      <!-- Top-left: Population -->
      <div data-testid="population-datapoint">
        <DataPoint
          id="city-population"
          label="Population"
          :value="populationHumanized"
          :raw-value="populationRaw"
          :trend-previous="populationTrendPrevious"
          :trend-next="populationTrendNext"
          source-label="Source: GHSL"
        />
      </div>

      <!-- Top-right: Density -->
      <div data-testid="density-datapoint">
        <DataPoint
          id="city-density"
          label="Density"
          :value="densityFormatted"
          :raw-value="density"
          :trend-previous="densityTrendPrevious"
          :trend-next="densityTrendNext"
          source-label="Source: GHSL"
        />
      </div>

      <!-- Bottom-left: Reserved empty space -->
      <div class="min-h-16">
        <!-- Reserved for future features -->
      </div>

      <!-- Bottom-right: Area -->
      <div data-testid="area-datapoint">
        <DataPoint
          id="city-area"
          label="Area"
          :value="areaFormatted"
          :raw-value="area"
          source-label="Source: GHSL"
        />
      </div>
    </div>
  </div>
</template>

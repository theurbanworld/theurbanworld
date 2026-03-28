<script setup lang="ts">
/**
 * ComparisonPanel — Full comparison sidebar content
 *
 * Composes the metric table, radial profile chart, and epoch sparklines
 * for two cities. Header shows both city names with identity colors.
 */

import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'

const props = defineProps<{
  cityIdA: string
  cityIdB: string
}>()

const { getCity } = useCitiesIndex()
const cityA = computed(() => getCity(props.cityIdA))
const cityB = computed(() => getCity(props.cityIdB))
</script>

<template>
  <div class="p-5 flex flex-col gap-5">
    <!-- City header with identity colors -->
    <header class="flex flex-col gap-1">
      <div class="flex items-center gap-2">
        <span
          class="w-2.5 h-2.5 rounded-full shrink-0"
          :class="CITY_A_COLOR.dotClass"
        />
        <h2 class="text-lg font-bold font-heading" :class="CITY_A_COLOR.textClass">
          {{ cityA?.name ?? 'City A' }}
        </h2>
      </div>
      <div class="flex items-center gap-2 pl-0.5">
        <span class="text-xs text-body/50 dark:text-cream/50">vs</span>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="w-2.5 h-2.5 rounded-full shrink-0"
          :class="CITY_B_COLOR.dotClass"
        />
        <h2 class="text-lg font-bold font-heading" :class="CITY_B_COLOR.textClass">
          {{ cityB?.name ?? 'City B' }}
        </h2>
      </div>
    </header>

    <!-- Column headers (city names above table) -->
    <div class="grid grid-cols-[auto_1fr_1fr] gap-x-3 items-baseline">
      <span class="w-16" />
      <div class="text-right">
        <span class="text-xs font-medium" :class="CITY_A_COLOR.textClass">
          {{ cityA?.name ?? 'A' }}
        </span>
      </div>
      <div class="text-right">
        <span class="text-xs font-medium" :class="CITY_B_COLOR.textClass">
          {{ cityB?.name ?? 'B' }}
        </span>
      </div>
    </div>

    <!-- Metric comparison table -->
    <ComparisonMetricTable
      :city-id-a="cityIdA"
      :city-id-b="cityIdB"
    />

    <!-- Radial profile overlay (will be extended in Unit 5) -->
    <div class="flex flex-col gap-1">
      <h3 class="text-xs font-medium text-body/70 dark:text-cream/70">
        Radial Density Profile
      </h3>
      <RadialProfileChart
        :city-id="cityIdA"
        :city-ids="[cityIdA, cityIdB]"
      />
    </div>

    <!-- Population sparkline overlay -->
    <div class="flex flex-col gap-1">
      <h3 class="text-xs font-medium text-body/70 dark:text-cream/70">
        Population
      </h3>
      <EpochSparkline
        :city-id="cityIdA"
        :city-ids="[cityIdA, cityIdB]"
        metric="population"
      />
    </div>

    <!-- Density sparkline overlay -->
    <div class="flex flex-col gap-1">
      <h3 class="text-xs font-medium text-body/70 dark:text-cream/70">
        Density
      </h3>
      <EpochSparkline
        :city-id="cityIdA"
        :city-ids="[cityIdA, cityIdB]"
        metric="density_per_km2"
      />
    </div>

    <!-- Area sparkline overlay -->
    <div class="flex flex-col gap-1">
      <h3 class="text-xs font-medium text-body/70 dark:text-cream/70">
        Area
      </h3>
      <EpochSparkline
        :city-id="cityIdA"
        :city-ids="[cityIdA, cityIdB]"
        metric="area_km2"
      />
    </div>
  </div>
</template>

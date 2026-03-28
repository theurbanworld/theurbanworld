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
    <!-- Column headers (city names with identity color dots) -->
    <div class="grid grid-cols-[auto_1fr_1fr] gap-x-3 items-center">
      <span class="w-16" />
      <div class="flex items-center justify-end gap-1.5">
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :class="CITY_A_COLOR.dotClass"
        />
        <span class="text-xs font-medium" :class="CITY_A_COLOR.textClass">
          {{ cityA?.name ?? 'A' }}
        </span>
      </div>
      <div class="flex items-center justify-end gap-1.5">
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :class="CITY_B_COLOR.dotClass"
        />
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

    <!-- Radial density profile overlay -->
    <div class="flex flex-col gap-1">
      <h3 class="text-xs font-medium text-body/70 dark:text-cream/70">
        Radial Density Profile
      </h3>
      <RadialProfileChart
        :city-id="cityIdA"
        :city-ids="[cityIdA, cityIdB]"
      />
    </div>
  </div>
</template>

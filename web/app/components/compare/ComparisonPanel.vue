<script setup lang="ts">
/**
 * ComparisonPanel — Full comparison sidebar content
 *
 * Composes the metric table, radial profile chart, and epoch sparklines
 * for two cities. Header shows both city names with identity colors.
 */

import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'

const { open: openInfoModal } = useInfoModal()

const props = defineProps<{
  cityIdA: string
  cityIdB: string
}>()

const { getCity } = useCitiesIndex()
const cityA = computed(() => getCity(props.cityIdA))
const cityB = computed(() => getCity(props.cityIdB))

// Swap modal state
const swapModalOpen = ref(false)
const swapSlot = ref<'a' | 'b'>('a')

/** The city that stays when swapping */
const keepCityId = computed(() =>
  swapSlot.value === 'a' ? props.cityIdB : props.cityIdA
)

function openSwap(slot: 'a' | 'b') {
  swapSlot.value = slot
  swapModalOpen.value = true
}

// Radial layer toggle for comparison maps
const { isComparisonRadialActive, setComparisonRadialActive } = useComparisonRadial()

function toggleRadialLayer() {
  setComparisonRadialActive(!isComparisonRadialActive.value)
}

// Deactivate when unmounting or cities change
onUnmounted(() => setComparisonRadialActive(false))
watch([() => props.cityIdA, () => props.cityIdB], () => setComparisonRadialActive(false))
</script>

<template>
  <div class="p-5 flex flex-col gap-5">
    <!-- Column headers (city names with identity color dots) -->
    <div class="grid grid-cols-[auto_1fr_1fr] gap-x-3 items-center">
      <span class="w-16" />
      <button
        class="flex items-center justify-end gap-1.5 cursor-pointer rounded px-1 -mx-1
               hover:bg-sand-100/60 dark:hover:bg-forest-900/30 transition-colors"
        title="Swap city"
        @click="openSwap('a')"
      >
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :class="CITY_A_COLOR.dotClass"
        />
        <span class="text-sm font-medium" :class="CITY_A_COLOR.textClass">
          {{ cityA?.name ?? 'A' }}
        </span>
      </button>
      <button
        class="flex items-center justify-end gap-1.5 cursor-pointer rounded px-1 -mx-1
               hover:bg-sand-100/60 dark:hover:bg-forest-900/30 transition-colors"
        title="Swap city"
        @click="openSwap('b')"
      >
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :class="CITY_B_COLOR.dotClass"
        />
        <span class="text-sm font-medium" :class="CITY_B_COLOR.textClass">
          {{ cityB?.name ?? 'B' }}
        </span>
      </button>
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
      <span
        class="text-xs text-body/50 dark:text-cream/50 hover:text-forest-600 dark:hover:text-forest-400 cursor-pointer transition-colors"
        @click="openInfoModal('/data/source-ghsl')"
      >
        Source: GHSL
      </span>
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
      <span
        class="text-xs text-body/50 dark:text-cream/50 hover:text-forest-600 dark:hover:text-forest-400 cursor-pointer transition-colors"
        @click="openInfoModal('/data/source-ghsl')"
      >
        Source: GHSL
      </span>
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
      <span
        class="text-xs text-body/50 dark:text-cream/50 hover:text-forest-600 dark:hover:text-forest-400 cursor-pointer transition-colors"
        @click="openInfoModal('/data/source-ghsl')"
      >
        Source: GHSL
      </span>
    </div>

    <!-- Radial density profile -->
    <div class="border-t border-border/30 dark:border-border/20 pt-4 flex flex-col gap-1">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-1.5">
          <h3 class="text-sm font-medium text-forest-700 dark:text-forest-300">
            Radial Profile
          </h3>
          <button
            class="text-body/40 dark:text-cream/40 hover:text-forest-600 dark:hover:text-forest-400 transition-colors cursor-pointer"
            aria-label="About radial profiles"
            @click="openInfoModal('/methodology/bertaud-radial')"
          >
            <UIcon name="i-lucide-info" class="w-3.5 h-3.5" />
          </button>
        </div>
        <button
          class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs cursor-pointer
                 transition-colors"
          :class="isComparisonRadialActive
            ? 'bg-forest-600 text-white dark:bg-forest-500'
            : 'text-body/60 dark:text-cream/60 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
          @click="toggleRadialLayer"
        >
          <UIcon name="i-lucide-map" class="w-3.5 h-3.5" />
          <span>{{ isComparisonRadialActive ? 'On map' : 'Show on map' }}</span>
        </button>
      </div>
      <RadialProfileChart
        :city-id="cityIdA"
        :city-ids="[cityIdA, cityIdB]"
      />
    </div>

    <!-- Swap city modal -->
    <CompareSearchModal
      v-model:open="swapModalOpen"
      :current-city-id="keepCityId"
    />
  </div>
</template>

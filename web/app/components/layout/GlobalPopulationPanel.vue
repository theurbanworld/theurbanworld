<script setup lang="ts">
/**
 * GlobalPopulationPanel - Left-anchored panel with world/urban population stats
 *
 * Positioned at top-left of the map area, hugging the sidebar edge and
 * the controls strip. Visibility controlled by useGlobalPopulationPanel
 * (toggle in the controls strip).
 */

const {
  worldPopulation,
  worldPopulationRaw,
  worldPopulationTrendPrevious,
  worldPopulationTrendNext,
  urbanPopulation,
  urbanPopulationRaw,
  urbanPopulationTrendPrevious,
  urbanPopulationTrendNext,
  urbanPercentageOfWorld,
  datasetUrbanPopulation
} = useGlobalStats()

const { isExpanded, toggle } = useGlobalPopulationPanel()
</script>

<template>
  <!-- Mobile-only floating toggle — the controls-strip dropdown is off-screen on mobile -->
  <button
    class="sm:hidden absolute z-110 left-0 top-0 flex flex-col items-start py-1.5 px-3
           bg-parchment/95 dark:bg-ink-950/95 backdrop-blur-sm
           border-r border-b border-ink-200/40 dark:border-ink-800/40
           rounded-br-xl shadow-lg
           active:scale-95 transition-transform cursor-pointer"
    :title="isExpanded ? 'Hide global stats' : 'Show global stats'"
    @click="toggle"
  >
    <span class="text-[10px] font-semibold uppercase tracking-wider leading-tight text-body/60 dark:text-cream/60">World Population</span>
    <span class="flex items-center gap-1">
      <span class="font-mono text-sm font-bold leading-tight text-ink-700 dark:text-ink-300 tracking-wide">
        {{ worldPopulation }}
      </span>
      <UIcon
        :name="isExpanded ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
        class="w-3.5 h-3.5 block text-body/50 dark:text-cream/50"
      />
    </span>
  </button>

  <div
    v-if="isExpanded"
    class="absolute z-100 left-0 top-0 w-72
           bg-parchment/95 dark:bg-ink-950/95 backdrop-blur-sm
           border-r border-b border-ink-200/40 dark:border-ink-800/40
           rounded-br-xl shadow-lg px-4 py-5
           max-sm:top-12 max-sm:w-auto max-sm:min-w-40"
  >
    <DataPoint
      id="world-population"
      label="World Population"
      :value="worldPopulation"
      :raw-value="worldPopulationRaw"
      :trend-previous="worldPopulationTrendPrevious"
      :trend-next="worldPopulationTrendNext"
      source-label="Source: UN WPP"
      content-path="/data/source-un-wpp"
    />

    <div class="h-4" />

    <DataPoint
      id="urban-population"
      label="Urban Population"
      :value="urbanPopulation"
      :raw-value="urbanPopulationRaw"
      :trend-previous="urbanPopulationTrendPrevious"
      :trend-next="urbanPopulationTrendNext"
      :percentage-value="urbanPercentageOfWorld"
      percentage-label="of"
      percentage-ref-label="World Population"
      percentage-ref-id="world-population"
      source-label="Source: UN WUP"
      content-path="/data/source-un-wup"
    >
      <div class="flex items-center gap-1 mt-1">
        <span class="font-mono text-xs font-medium text-ink-600/70 dark:text-ink-400/70">
          {{ datasetUrbanPopulation }}
        </span>
        <span class="text-xs text-body/50 dark:text-cream/50">
          in our dataset
        </span>
      </div>
    </DataPoint>
  </div>
</template>

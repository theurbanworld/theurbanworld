<script setup lang="ts">
/**
 * GlobalPopulationPanel - Right-anchored panel with world/urban population stats
 *
 * Positioned at top-right of the map area, hugging the right edge.
 * Visibility controlled by useGlobalPopulationPanel (toggle in the controls strip).
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

const { isExpanded } = useGlobalPopulationPanel()
</script>

<template>
  <div
    v-if="isExpanded"
    class="absolute z-100 right-0 top-0 w-72
           bg-parchment/95 dark:bg-ink-950/95 backdrop-blur-sm
           border-l border-b border-ink-200/40 dark:border-ink-800/40
           rounded-bl-xl shadow-lg px-4 py-5
           max-sm:w-auto max-sm:min-w-40"
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

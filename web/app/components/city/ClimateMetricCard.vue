<script setup lang="ts">
/**
 * ClimateMetricCard — renders one climate metric, dispatched by temporal class.
 *
 *   series      -> latest value + NativeAxisSparkline (own year keys)
 *   projection  -> ProjectionToggle (now / future, modeled qualifier)
 *   snapshot    -> single stat (no implied trend); LCZ renders as labelled parts
 *
 * Absent value -> "not available for this city" (R13). Modeled metrics show the
 * catalog-driven qualifier (R15). The source label opens the methodology modal
 * via the descriptor's methodologyPath (R14 / U8).
 */

import type {
  ClimateMetricDescriptor,
  ClimateMetricValue,
  SeriesValue,
  ProjectionValue,
  SnapshotValue,
  CompositionValue
} from '../../../types/climate'
import {
  formatClimateValue,
  latestValue,
  MODELED_QUALIFIER,
  type SeriesPoint
} from '../../utils/climateFormat'

const props = defineProps<{
  descriptor: ClimateMetricDescriptor
  value?: ClimateMetricValue
}>()

const { open: openInfoModal } = useInfoModal()

const available = computed(() => props.value != null)

const seriesPoints = computed<SeriesPoint[]>(() =>
  props.descriptor.temporalClass === 'series' ? (props.value as SeriesValue)?.points ?? [] : []
)
const seriesLatest = computed(() => formatClimateValue(latestValue(seriesPoints.value), props.descriptor.unit))

const projection = computed(() =>
  props.descriptor.temporalClass === 'projection' ? (props.value as ProjectionValue) : null
)

const snapshotText = computed(() =>
  formatClimateValue((props.value as SnapshotValue)?.value ?? null, props.descriptor.unit)
)

// LCZ-style composition: top parts by share
const compositionParts = computed(() => {
  const parts = (props.value as CompositionValue)?.parts ?? []
  return [...parts].sort((a, b) => b[1] - a[1]).slice(0, 4)
})
const isComposition = computed(() => props.descriptor.key === 'lcz_composition')

// Modeled qualifier: shown for modeled metrics except projections (the
// ProjectionToggle already renders its own qualifier).
const showModeledQualifier = computed(
  () => props.descriptor.modeled && props.descriptor.temporalClass !== 'projection'
)
</script>

<template>
  <div
    class="flex flex-col gap-1"
    data-testid="climate-metric-card"
    :data-metric="descriptor.key"
  >
    <span class="text-sm text-body/70 dark:text-cream/70">{{ descriptor.label }}</span>

    <!-- Unavailable -->
    <span
      v-if="!available"
      data-testid="climate-metric-unavailable"
      class="text-xs italic text-body/40 dark:text-cream/40"
    >
      Not available for this city
    </span>

    <!-- Projection -->
    <ProjectionToggle
      v-else-if="projection"
      :now="projection.now"
      :future="projection.future"
      :future-label="descriptor.futureLabel"
      :unit="descriptor.unit"
    />

    <!-- Series -->
    <template v-else-if="descriptor.temporalClass === 'series'">
      <span class="font-mono text-2xl font-semibold text-ink-700 dark:text-ink-300">
        {{ seriesLatest }}
      </span>
      <NativeAxisSparkline
        :points="seriesPoints"
        :unit="descriptor.unit"
        :label="descriptor.label"
      />
    </template>

    <!-- Snapshot: LCZ composition -->
    <div
      v-else-if="isComposition"
      data-testid="climate-metric-composition"
      class="flex flex-col gap-0.5"
    >
      <span
        v-for="part in compositionParts"
        :key="part[0]"
        class="text-xs text-body/70 dark:text-cream/70"
      >
        {{ part[0] }} · {{ part[1].toFixed(0) }}%
      </span>
    </div>

    <!-- Snapshot: single stat -->
    <span
      v-else
      class="font-mono text-2xl font-semibold text-ink-700 dark:text-ink-300"
    >
      {{ snapshotText }}
    </span>

    <!-- Modeled qualifier (catalog-driven) -->
    <span
      v-if="available && showModeledQualifier"
      data-testid="climate-metric-modeled"
      class="text-[10px] italic text-body/50 dark:text-cream/50"
    >
      {{ MODELED_QUALIFIER }}
    </span>

    <!-- Source / methodology link -->
    <button
      data-testid="climate-metric-source"
      class="self-start text-xs text-body/50 dark:text-cream/50 hover:text-ink-600 dark:hover:text-ink-400 cursor-pointer transition-colors"
      @click="openInfoModal(descriptor.methodologyPath)"
    >
      {{ descriptor.source }}
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * ClimateMetricGroup — one collapsible lens of supporting climate metrics.
 *
 * Collapsed by default (supporting depth, not headline). Renders nothing if the
 * city has none of this lens's metrics, so low-coverage cities don't show empty
 * groups; within a partially-covered lens, absent metrics render their
 * per-metric "not available" state (e.g. marine metrics for an inland city).
 */

import type { ClimateMetricDescriptor, ClimateRecord } from '../../../types/climate'

const props = defineProps<{
  label: string
  metrics: ClimateMetricDescriptor[]
  record: ClimateRecord | null
  defaultOpen?: boolean
}>()

const open = ref(props.defaultOpen ?? false)

const hasAny = computed(() => props.metrics.some(m => props.record?.[m.key] != null))
</script>

<template>
  <div
    v-if="hasAny"
    data-testid="climate-metric-group"
    :data-lens-label="label"
    class="border-t border-border/20 dark:border-border/10 pt-3"
  >
    <button
      class="flex items-center justify-between w-full text-left cursor-pointer group"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="text-sm font-medium text-ink-700 dark:text-ink-300">{{ label }}</span>
      <UIcon
        :name="open ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
        class="w-4 h-4 text-body/40 dark:text-cream/40 group-hover:text-ink-600 dark:group-hover:text-ink-400 transition-colors"
      />
    </button>

    <div
      v-show="open"
      class="flex flex-col gap-4 mt-3"
    >
      <ClimateMetricCard
        v-for="metric in metrics"
        :key="metric.key"
        :descriptor="metric"
        :value="record?.[metric.key]"
      />
    </div>
  </div>
</template>

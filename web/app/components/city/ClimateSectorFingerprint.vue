<script setup lang="ts">
/**
 * ClimateSectorFingerprint — a compact stacked bar of CO₂ sector shares.
 *
 * The inline companion to the per-capita CO₂ headline (R15): the two cannot
 * ship apart, so ClimateEnergySection composes this directly under the headline.
 * Shows what drives the number (energy / transport / industry / residential) —
 * the least population-circular signal in the emissions data.
 */

import type { SectorValue } from '../../../types/climate'
import { normalizeSectors } from '../../utils/climateFormat'

const props = defineProps<{
  value: SectorValue
}>()

// Muted, distinct segment colors aligned with the section's ink palette.
const COLORS = ['#4A5B6A', '#7B8B98', '#A8744F', '#C9A227']

const shares = computed(() => normalizeSectors(props.value?.sectors ?? []))
</script>

<template>
  <div
    v-if="shares.length"
    data-testid="sector-fingerprint"
    class="flex flex-col gap-1"
  >
    <!-- stacked bar -->
    <div class="flex h-2.5 w-full overflow-hidden rounded-full">
      <div
        v-for="(s, i) in shares"
        :key="s.label"
        :style="{ width: `${s.pct}%`, backgroundColor: COLORS[i % COLORS.length] }"
        :title="`${s.label}: ${s.pct.toFixed(0)}%`"
      />
    </div>
    <!-- legend -->
    <div class="flex flex-wrap gap-x-3 gap-y-0.5">
      <span
        v-for="(s, i) in shares"
        :key="s.label"
        class="flex items-center gap-1 text-[10px] text-body/60 dark:text-cream/60"
      >
        <span
          class="inline-block h-2 w-2 rounded-sm"
          :style="{ backgroundColor: COLORS[i % COLORS.length] }"
        />
        {{ s.label }} {{ s.pct.toFixed(0) }}%
      </span>
    </div>
  </div>
</template>

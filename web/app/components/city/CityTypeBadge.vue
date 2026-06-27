<script setup lang="ts">
/**
 * CityTypeBadge - two-axis Standard Urban Model badge with honest-null.
 *
 * Reads the fitted metrics for the selected epoch and shows two plain-language
 * labels (compactness + structure). Has three explicit states so a still-loading
 * fit is never mislabelled as unreliable:
 *   - loading    → neutral placeholder, no note
 *   - unreliable → "fit not reliable here" note (badge + curve suppressed)
 *   - reliable   → both labels
 *
 * All reads key off useSelectedYear, so scrubbing the epoch slider re-derives the
 * badge automatically.
 */

import { compactnessLabel, structureLabel, fitBadgeState } from '~/utils/urbanModelLabels'

const props = defineProps<{ cityId: string }>()

const { selectedYear } = useSelectedYear()
const { getFit } = useUrbanModelFit()

const fit = computed(() => getFit(props.cityId, selectedYear.value))
const state = computed(() => fitBadgeState(fit.value))

const compactness = computed(() =>
  state.value === 'reliable' ? compactnessLabel(fit.value!.beta) : null
)
const structure = computed(() =>
  state.value === 'reliable' ? structureLabel(fit.value!.r2) : null
)
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-1.5 text-xs"
    data-testid="city-type-badge"
  >
    <span class="text-body/50 dark:text-cream/50">Urban model</span>

    <!-- reliable: two labels -->
    <template v-if="state === 'reliable'">
      <span
        data-testid="badge-compactness"
        class="px-2 py-0.5 rounded-full font-medium bg-ink-100/60 dark:bg-ink-900/40 text-ink-700 dark:text-ink-300"
      >
        {{ compactness }}
      </span>
      <span
        data-testid="badge-structure"
        class="px-2 py-0.5 rounded-full font-medium bg-ink-100/60 dark:bg-ink-900/40 text-ink-700 dark:text-ink-300"
      >
        {{ structure }}
      </span>
    </template>

    <!-- unreliable: honest-null note -->
    <span
      v-else-if="state === 'unreliable'"
      data-testid="badge-note"
      class="italic text-body/50 dark:text-cream/50"
    >
      Fit not reliable here
    </span>

    <!-- loading / absent: neutral placeholder, no note -->
    <span
      v-else
      data-testid="badge-placeholder"
      class="px-2 py-0.5 rounded-full bg-ink-100/30 dark:bg-ink-900/20 text-body/30 dark:text-cream/30"
    >
      —
    </span>
  </div>
</template>

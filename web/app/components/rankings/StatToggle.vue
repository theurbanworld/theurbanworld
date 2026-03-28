<script setup lang="ts">
/**
 * StatToggle - Population/Density/Area/Growth ranking stat buttons
 *
 * Sits in the search strip's left column, matching the sidebar width.
 * Shares state with CityRankings via useRankingFilters composable.
 */

import type { RankingStat } from '~/composables/useRankingFilters'

const { activeStat } = useRankingFilters()

const stats: { key: RankingStat; label: string }[] = [
  { key: 'population', label: 'Population' },
  { key: 'density', label: 'Density' },
  { key: 'area', label: 'Area' },
  { key: 'growth', label: 'Growth' }
]
</script>

<template>
  <div class="w-96 shrink-0 flex items-center gap-1 px-4 border-r border-ink-200/40 dark:border-ink-800/40 max-sm:hidden">
    <button
      v-for="stat in stats"
      :key="stat.key"
      class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer"
      :class="activeStat === stat.key
        ? 'bg-ink-700 text-white dark:bg-ink-400 dark:text-ink-950'
        : 'text-body/70 dark:text-cream/70 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
      @click="activeStat = stat.key"
    >
      {{ stat.label }}
    </button>
  </div>
</template>

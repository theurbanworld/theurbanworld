<script setup lang="ts">
/**
 * StatToggle - Population/Density/Area ranking stat buttons
 *
 * Sits in the search strip's left column, matching the sidebar width.
 * Shares state with CityRankings via useRankingFilters composable.
 */

import type { RankingStat } from '~/composables/useRankingFilters'

const { activeStat } = useRankingFilters()

const stats: { key: RankingStat; label: string }[] = [
  { key: 'population', label: 'Population' },
  { key: 'density', label: 'Density' },
  { key: 'area', label: 'Area' }
]
</script>

<template>
  <div class="w-80 shrink-0 flex items-center gap-1 px-4 border-r border-forest-200/40 dark:border-forest-800/40 max-sm:hidden">
    <button
      v-for="stat in stats"
      :key="stat.key"
      class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer"
      :class="activeStat === stat.key
        ? 'bg-forest-700 text-white dark:bg-forest-400 dark:text-forest-950'
        : 'text-body/70 dark:text-cream/70 hover:bg-forest-100/50 dark:hover:bg-forest-900/30'"
      @click="activeStat = stat.key"
    >
      {{ stat.label }}
    </button>
  </div>
</template>

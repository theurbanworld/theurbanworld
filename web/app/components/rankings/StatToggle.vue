<script setup lang="ts">
/**
 * StatToggle - Population/Density/Area/Growth ranking stat buttons
 *
 * Sits in the search strip's left column, matching the sidebar width.
 * Shares state with CityRankings via useRankingFilters composable.
 * Growth has a nested sub-toggle for rate vs absolute mode.
 */

import type { RankingStat, GrowthMode } from '~/composables/useRankingFilters'

const { activeStat, growthMode } = useRankingFilters()

const stats: { key: RankingStat; label: string }[] = [
  { key: 'population', label: 'Population' },
  { key: 'density', label: 'Density' },
  { key: 'area', label: 'Area' },
  { key: 'growth', label: 'Growth' }
]

const growthModes: { key: GrowthMode; label: string }[] = [
  { key: 'rate', label: '%/yr' },
  { key: 'abs', label: 'Abs' }
]
</script>

<template>
  <div class="w-96 shrink-0 flex items-center gap-1 px-4 border-r border-ink-200/40 dark:border-ink-800/40 max-sm:hidden">
    <template v-for="stat in stats" :key="stat.key">
      <button
        v-if="stat.key !== 'growth'"
        class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer"
        :class="activeStat === stat.key
          ? 'bg-ink-700 text-white dark:bg-ink-400 dark:text-ink-950'
          : 'text-body/70 dark:text-cream/70 hover:bg-ink-100/50 dark:hover:bg-ink-900/30'"
        @click="activeStat = stat.key"
      >
        {{ stat.label }}
      </button>

      <!-- Growth button with inline sub-toggle when active -->
      <button
        v-else-if="activeStat !== 'growth'"
        class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer
               text-body/70 dark:text-cream/70 hover:bg-ink-100/50 dark:hover:bg-ink-900/30"
        @click="activeStat = 'growth'"
      >
        Growth
      </button>
      <div
        v-else
        class="flex items-stretch rounded-md overflow-hidden bg-ink-700/8 dark:bg-ink-400/8"
      >
        <button
          class="px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer
                 bg-ink-700 text-white dark:bg-ink-400 dark:text-ink-950"
          @click="activeStat = 'growth'"
        >
          Growth
        </button>
        <button
          v-for="mode in growthModes"
          :key="mode.key"
          class="px-1.5 py-1.5 text-[10px] font-medium transition-colors cursor-pointer"
          :class="growthMode === mode.key
            ? 'bg-ink-700/15 text-ink-800 dark:bg-ink-400/15 dark:text-ink-200'
            : 'text-ink-400 dark:text-ink-600 hover:text-ink-600 dark:hover:text-ink-400'"
          @click="growthMode = mode.key"
        >
          {{ mode.label }}
        </button>
      </div>
    </template>
  </div>
</template>

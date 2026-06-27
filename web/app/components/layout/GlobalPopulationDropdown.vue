<script setup lang="ts">
/**
 * GlobalPopulationDropdown - Toggle button for the global population panel
 *
 * Displays "World Population" + humanized number in the controls strip.
 * Clicking toggles the panel (rendered separately in the layout).
 */

const { worldPopulation } = useGlobalStats()
const { isExpanded, toggle } = useGlobalPopulationPanel()
</script>

<template>
  <button
    class="flex flex-col items-start py-1 px-2 -mr-2 rounded-md
           hover:bg-ink-100/50 dark:hover:bg-ink-900/30
           transition-colors cursor-pointer"
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
</template>

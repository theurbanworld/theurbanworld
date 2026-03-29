<script setup lang="ts">
/**
 * DataAttribution — compact map attribution bar
 *
 * Shows legally required attribution for OSM, Protomaps, GHSL, and MapLibre.
 * GHSL opens the info modal (consistent with other Source links);
 * external projects open in new tabs.
 * Collapses to a single © icon on small screens.
 */

const { open: openInfoModal } = useInfoModal()
const expanded = ref(false)
</script>

<template>
  <div class="absolute bottom-2.5 right-2.5 z-10">
    <!-- Collapsed: just © button (shown on small screens) -->
    <button
      class="sm:hidden px-2 py-1 rounded bg-parchment/80 dark:bg-forest-950/80
             backdrop-blur-sm text-xs text-body/60 dark:text-cream/60 shadow-sm"
      :aria-label="expanded ? 'Collapse attribution' : 'Expand attribution'"
      @click="expanded = !expanded"
    >
      ©
    </button>

    <!-- Expanded row (always on sm+, toggled on mobile) -->
    <div
      :class="[
        'flex items-center gap-1 px-2 py-1 rounded',
        'bg-parchment/80 dark:bg-forest-950/80 backdrop-blur-sm shadow-sm',
        'text-[10px] leading-tight text-body/50 dark:text-cream/50',
        expanded ? '' : 'hidden sm:flex'
      ]"
    >
      <a
        href="https://www.openstreetmap.org/copyright"
        target="_blank"
        rel="noopener"
        class="hover:text-ink-600 dark:hover:text-ink-400 transition-colors"
      >© OpenStreetMap</a>
      <span class="text-body/30 dark:text-cream/30">·</span>
      <a
        href="https://protomaps.com"
        target="_blank"
        rel="noopener"
        class="hover:text-ink-600 dark:hover:text-ink-400 transition-colors"
      >Protomaps</a>
      <span class="text-body/30 dark:text-cream/30">·</span>
      <button
        class="hover:text-ink-600 dark:hover:text-ink-400 transition-colors cursor-pointer"
        @click="openInfoModal('/data/source-ghsl')"
      >GHSL</button>
      <span class="text-body/30 dark:text-cream/30">·</span>
      <a
        href="https://maplibre.org"
        target="_blank"
        rel="noopener"
        class="hover:text-ink-600 dark:hover:text-ink-400 transition-colors"
      >MapLibre</a>
    </div>
  </div>
</template>

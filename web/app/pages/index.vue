<script setup lang="ts">
/**
 * Home page
 *
 * Route: /
 *
 * Triggers data loading for city index and populations.
 * Rankings UI is rendered in the sidebar via app.vue.
 */

useSeoMeta({
  title: 'The Urban World',
  description: 'an observatory of urban complexity',
  ogDescription: 'an observatory of urban complexity'
})

const { clearSelection } = useCitySelection()

onMounted(() => {
  clearSelection()
})

const { execute: loadCitiesIndex } = useCitiesIndex()
const { execute: loadPopulations } = useCityPopulations()

// Load the large datasets (index ~2 MB, populations ~14 MB) on the CLIENT only.
// They feed the interactive map and rankings sidebar (client-only components);
// fetching them during SSR would serialize both into the hydration payload and
// bloat the HTML past the 5 MB limit crawlers and OG scrapers enforce.
if (import.meta.client) {
  loadCitiesIndex()
  loadPopulations()
}
</script>

<template>
  <div />
</template>

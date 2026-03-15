<script setup lang="ts">
/**
 * Home page — City Rankings
 *
 * Route: /
 *
 * Triggers data loading for city index and populations.
 * Rankings UI is rendered in the sidebar via app.vue.
 */

useSeoMeta({
  title: 'City Rankings — The Urban World',
  description: 'Explore the world\'s cities ranked by population, density, and area.'
})

const { clearSelection } = useCitySelection()

onMounted(() => {
  clearSelection()
})

const { execute: loadCitiesIndex } = useCitiesIndex()
const { execute: loadPopulations } = useCityPopulations()

await Promise.all([
  loadCitiesIndex(),
  loadPopulations()
])
</script>

<template>
  <div />
</template>

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

await Promise.all([
  loadCitiesIndex(),
  loadPopulations()
])
</script>

<template>
  <div />
</template>

<script setup lang="ts">
/**
 * City view page
 *
 * Route: /city/[city_id]
 *
 * Triggers data loading for city statistics (SSR-compatible via useAsyncData).
 * Syncs route params with city selection state.
 * The sidebar and map are rendered in app.vue.
 */

// Get route params
const route = useRoute()

// Get city selection state
const { selectCity } = useCitySelection()

// Get data loading functions
const { execute: loadCitiesIndex } = useCitiesIndex()
const { execute: loadPopulations } = useCityPopulations()
const { execute: loadRadialProfiles } = useRadialProfiles()

// Extract city_id from route params
const cityId = computed(() => {
  const id = route.params.city_id
  return Array.isArray(id) ? id[0] : id
})

// Load data (SSR-compatible, deduped via useAsyncData keys)
await Promise.all([
  loadCitiesIndex(),
  loadPopulations(),
  loadRadialProfiles()
])

// City lookup for SEO
const { getCity } = useCitiesIndex()
const city = computed(() => cityId.value ? getCity(cityId.value) : undefined)

useSeoMeta({
  title: () => city.value
    ? `${city.value.name}, ${city.value.country} — The Urban World`
    : 'City — The Urban World',
  description: () => city.value
    ? `Urban density, population trends, and growth patterns for ${city.value.name}, ${city.value.country}.`
    : 'Explore urban density, population, and growth patterns.'
})

// Sync route param to city selection state
watchEffect(() => {
  if (cityId.value) {
    selectCity(cityId.value)
  }
})
</script>

<template>
  <!-- Route-specific content rendered here if needed -->
  <div />
</template>

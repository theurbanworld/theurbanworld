<script setup lang="ts">
/**
 * City view page
 *
 * Route: /city/[city_id]
 *
 * Fetches lightweight city metadata server-side for SEO (meta tags,
 * OG images, schema.org). Triggers full data loading client-side
 * for the interactive map and sidebar.
 * Syncs route params with city selection state.
 */
import { humanizeNumber } from '~/composables/useGlobalStats'

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

// SSR-compatible city metadata (lightweight, ~200 bytes)
const { data: cityMeta } = await useAsyncData(
  `city-meta-${cityId.value}`,
  () => $fetch(`/api/city/${cityId.value}`)
)

// Load interactive data (client-only, deduped via useAsyncData keys)
await Promise.all([
  loadCitiesIndex(),
  loadPopulations(),
  loadRadialProfiles()
])

// SEO meta tags — use SSR-compatible cityMeta
useSeoMeta({
  title: () => cityMeta.value
    ? `${cityMeta.value.name}, ${cityMeta.value.country} — The Urban World`
    : 'City — The Urban World',
  description: () => cityMeta.value
    ? `Urban density, population trends, and growth patterns for ${cityMeta.value.name}, ${cityMeta.value.country}.`
    : 'Explore urban density, population, and growth patterns.'
})

// OG image — uses cityMeta (available during SSR) for name/country,
// and population data for stats (resolved by awaits above)
const { getCityPopulationData } = useCityPopulations()
const popData = cityId.value ? getCityPopulationData(cityId.value, 2025) : undefined

defineOgImage('City', {
  cityName: cityMeta.value?.name ?? '',
  countryName: cityMeta.value?.country ?? '',
  population: popData ? humanizeNumber(popData.population) : '',
  density: popData
    ? (popData.density_per_km2 >= 1000
        ? `${Math.round(popData.density_per_km2 / 100) / 10} K/km2`
        : `${Math.round(popData.density_per_km2)}/km2`)
    : '',
  area: popData ? `${Math.round(popData.area_km2).toLocaleString()} km2` : '',
  outlineUrl: `https://data.theurban.world/data/outlines/${cityId.value}.json`
})

// Schema.org structured data — City entity (SSR-compatible via cityMeta)
const schemaOrgNodes = computed(() => {
  if (!cityMeta.value) return []

  const city = cityMeta.value
  const node: Record<string, unknown> = {
    '@type': 'City',
    'name': city.name,
    'url': `https://theurban.world/city/${city.id}`,
    'containedInPlace': {
      '@type': 'Country',
      'name': city.country
    },
    'identifier': {
      '@type': 'PropertyValue',
      'propertyID': 'GHS-UCDB',
      'value': city.id
    }
  }

  if (city.centroid) {
    node.geo = {
      '@type': 'GeoCoordinates',
      'latitude': city.centroid[1],
      'longitude': city.centroid[0]
    }
  }

  if (city.population) {
    node.additionalProperty = [{
      '@type': 'PropertyValue',
      'name': 'population',
      'value': city.population,
      'unitText': 'people'
    }]
  }

  // Wikidata sameAs (populated once pipeline adds wikidata_id)
  if (city.wikidata_id) {
    node.sameAs = [`https://www.wikidata.org/wiki/${city.wikidata_id}`]
  }

  return [node]
})

useSchemaOrg(schemaOrgNodes)

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

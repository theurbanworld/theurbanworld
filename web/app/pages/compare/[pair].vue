<script setup lang="ts">
/**
 * City comparison page
 *
 * Route: /compare/[pair] where pair is "id1+id2"
 *
 * Parses city IDs from URL, handles redirects (canonical ordering,
 * same-city), loads data, and renders the comparison layout.
 */
import { humanizeNumber } from '~/composables/useGlobalStats'

definePageMeta({
  layout: 'compare'
})

// Comparison state from route
const { cityA, cityB, isValid, isLoading, hasInvalidCities, redirect, parseError } = useComparisonState()

// Handle redirects (canonical ordering, same-city)
if (redirect.value) {
  await navigateTo(redirect.value.target, { replace: true, redirectCode: 301 })
}

// Handle parse errors (missing separator, non-numeric)
if (parseError.value) {
  await navigateTo('/', { replace: true })
}

// Load data (client-only, same pattern as city page)
const { execute: loadCitiesIndex } = useCitiesIndex()
const { execute: loadPopulations } = useCityPopulations()
const { execute: loadRadialProfiles } = useRadialProfiles()

await Promise.all([
  loadCitiesIndex(),
  loadPopulations(),
  loadRadialProfiles()
])

// After data loads, check if cities are valid
watchEffect(() => {
  if (hasInvalidCities.value) {
    navigateTo('/', { replace: true })
  }
})

// SEO meta
const { getCity } = useCitiesIndex()
const cityAData = computed(() => cityA.value ? getCity(cityA.value) : undefined)
const cityBData = computed(() => cityB.value ? getCity(cityB.value) : undefined)

useSeoMeta({
  title: () => {
    if (cityAData.value && cityBData.value) {
      return `${cityAData.value.name} vs ${cityBData.value.name} — The Urban World`
    }
    return 'City Comparison — The Urban World'
  },
  description: () => {
    if (cityAData.value && cityBData.value) {
      return `Compare urban density, population, and growth between ${cityAData.value.name} and ${cityBData.value.name}.`
    }
    return 'Compare cities by population, density, area, and growth patterns.'
  }
})

// OG image — City A stats (left), City B stats (right), outlines overlaid in
// the center. Mirrors the city-page formatting; data is awaited above so these
// resolve during SSR.
const { getCityPopulationData } = useCityPopulations()

function ogStatsFor(cityId: string | null | undefined) {
  const pop = cityId ? getCityPopulationData(cityId, 2025) : undefined
  return {
    population: pop ? humanizeNumber(pop.population) : '',
    density: pop
      ? (pop.density_per_km2 >= 1000
          ? `${Math.round(pop.density_per_km2 / 100) / 10} K/km2`
          : `${Math.round(pop.density_per_km2)}/km2`)
      : '',
    area: pop ? `${Math.round(pop.area_km2).toLocaleString()} km2` : ''
  }
}

const ogA = ogStatsFor(cityA.value)
const ogB = ogStatsFor(cityB.value)

defineOgImage('Comparison', {
  cityAName: cityAData.value?.name ?? '',
  cityACountry: cityAData.value?.country ?? '',
  cityAPopulation: ogA.population,
  cityADensity: ogA.density,
  cityAArea: ogA.area,
  cityAOutlineUrl: cityA.value ? `https://data.theurban.world/data/outlines/${cityA.value}.json` : '',
  cityBName: cityBData.value?.name ?? '',
  cityBCountry: cityBData.value?.country ?? '',
  cityBPopulation: ogB.population,
  cityBDensity: ogB.density,
  cityBArea: ogB.area,
  cityBOutlineUrl: cityB.value ? `https://data.theurban.world/data/outlines/${cityB.value}.json` : ''
})

// Layout reads useComparisonState() directly (layout is parent, can't inject from child)
</script>

<template>
  <div>
    <!-- Comparison sidebar content (renders inside AppSidebar via layout slot) -->
    <ComparisonPanel
      v-if="isValid && cityA && cityB"
      :city-id-a="cityA"
      :city-id-b="cityB"
    />
    <!-- Loading state while cities index loads -->
    <div
      v-else-if="isLoading"
      class="flex items-center justify-center p-8"
    >
      <p class="text-body/50 dark:text-cream/50 text-sm">
        Loading comparison...
      </p>
    </div>
  </div>
</template>

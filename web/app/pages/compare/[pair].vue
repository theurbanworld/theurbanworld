<script setup lang="ts">
/**
 * City comparison page
 *
 * Route: /compare/[pair] where pair is "id1+id2"
 *
 * Parses city IDs from URL, handles redirects (canonical ordering,
 * same-city), loads data, and renders the comparison layout.
 */

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

// Provide comparison city IDs to layout via injection
provide('comparisonCityA', cityA)
provide('comparisonCityB', cityB)
provide('comparisonIsValid', isValid)
provide('comparisonIsLoading', isLoading)
</script>

<template>
  <div>
    <!-- Loading state while cities index loads -->
    <div v-if="isLoading" class="flex items-center justify-center h-full">
      <p class="text-body/50 dark:text-cream/50">Loading comparison...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatPopulation } from '~/utils/formatNumber'

const { searchTerm, results } = useCitySearch()

const items = computed(() =>
  results.value.map(({ city }) => ({
    label: city.name,
    description: `${city.country} · ${formatPopulation(city.population)}`,
    value: city.id
  }))
)

function onSelect(item: { value: string } | undefined) {
  if (!item) return
  navigateTo(`/city/${item.value}`)
}
</script>

<template>
  <UInputMenu
    v-model:search-term="searchTerm"
    :model-value="undefined"
    :items="items"
    ignore-filter
    icon="i-lucide-search"
    placeholder="Search cities..."
    trailing-icon=""
    selected-icon=""
    open-on-focus
    :reset-search-term-on-blur="false"
    class="w-full"
    @update:model-value="onSelect"
  />
</template>

<script setup lang="ts">
/**
 * CompareSearchModal — City picker modal for comparison entry
 *
 * Reuses the Fuse.js search from useCitySearch but navigates
 * to /compare/[id1]+[id2] instead of /city/[id].
 */

import { formatPopulation } from '~/utils/formatNumber'

const props = defineProps<{
  /** The city currently being viewed (to exclude from results) */
  currentCityId: string
}>()

const open = defineModel<boolean>('open', { default: false })

const { searchTerm, results } = useCitySearch()

const items = computed(() =>
  results.value
    .filter(({ city }) => city.id !== props.currentCityId)
    .map(({ city }) => ({
      label: city.name,
      description: `${city.country} · ${formatPopulation(city.population)}`,
      value: city.id
    }))
)

function onSelect(item: { value: string } | undefined) {
  if (!item) return
  open.value = false
  searchTerm.value = ''

  // Canonical ordering: lower numeric ID first
  const idA = parseInt(props.currentCityId, 10)
  const idB = parseInt(item.value, 10)
  const [first, second] = idA < idB
    ? [props.currentCityId, item.value]
    : [item.value, props.currentCityId]

  navigateTo(`/compare/${first}+${second}`)
}

// Reset search when modal opens
watch(open, (isOpen) => {
  if (isOpen) {
    searchTerm.value = ''
  }
})
</script>

<template>
  <UModal v-model:open="open" title="Compare with..." description="Search for a city to compare">
    <template #body>
      <UInputMenu
        v-model:search-term="searchTerm"
        :model-value="undefined"
        :items="items"
        ignore-filter
        icon="i-lucide-search"
        placeholder="Search cities..."
        trailing-icon=""
        selected-icon=""
        autofocus
        :reset-search-term-on-blur="false"
        class="w-full"
        @update:model-value="onSelect"
      />
    </template>
  </UModal>
</template>

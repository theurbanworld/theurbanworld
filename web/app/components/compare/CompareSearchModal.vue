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

const highlightedIndex = ref(-1)
const inputRef = ref<HTMLInputElement | null>(null)

const items = computed(() =>
  results.value
    .filter(({ city }) => city.id !== props.currentCityId)
    .map(({ city }) => ({
      label: city.name,
      description: `${city.country} · ${formatPopulation(city.population)}`,
      value: city.id
    }))
)

function onSelect(item: { value: string }) {
  open.value = false
  searchTerm.value = ''
  highlightedIndex.value = -1

  // Canonical ordering: lower numeric ID first
  const idA = parseInt(props.currentCityId, 10)
  const idB = parseInt(item.value, 10)
  const [first, second] = idA < idB
    ? [props.currentCityId, item.value]
    : [item.value, props.currentCityId]

  navigateTo(`/compare/${first}+${second}`)
}

function onKeydown(e: KeyboardEvent) {
  if (!items.value.length) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlightedIndex.value = (highlightedIndex.value + 1) % items.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlightedIndex.value = highlightedIndex.value <= 0
      ? items.value.length - 1
      : highlightedIndex.value - 1
  } else if (e.key === 'Enter' && highlightedIndex.value >= 0) {
    e.preventDefault()
    const item = items.value[highlightedIndex.value]
    if (item) onSelect(item)
  }
}

// Reset search when modal opens
watch(open, (isOpen) => {
  if (isOpen) {
    searchTerm.value = ''
    highlightedIndex.value = -1
    nextTick(() => inputRef.value?.focus())
  }
})

watch(searchTerm, () => {
  highlightedIndex.value = -1
})
</script>

<template>
  <UModal v-model:open="open" title="Compare with..." description="Search for a city to compare">
    <template #body>
      <div class="relative">
        <div class="relative">
          <UIcon
            name="i-lucide-search"
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400 dark:text-ink-500 pointer-events-none"
          />
          <input
            ref="inputRef"
            v-model="searchTerm"
            type="text"
            placeholder="Search cities..."
            class="w-full pl-9 pr-3 py-2 text-sm rounded-md
                   bg-white dark:bg-ink-900
                   border border-ink-200 dark:border-ink-700
                   text-ink-700 dark:text-ink-200
                   placeholder:text-ink-400 dark:placeholder:text-ink-500
                   focus:outline-none focus:ring-2 focus:ring-ink-400/40 dark:focus:ring-ink-500/40
                   transition"
            @keydown="onKeydown"
          />
        </div>

        <ul
          v-if="items.length"
          class="mt-2 max-h-64 overflow-y-auto rounded-md
                 border border-ink-200 dark:border-ink-700
                 py-1"
        >
          <li
            v-for="(item, i) in items"
            :key="item.value"
            class="px-3 py-2 cursor-pointer transition-colors"
            :class="i === highlightedIndex
              ? 'bg-ink-100 dark:bg-ink-800'
              : 'hover:bg-ink-50 dark:hover:bg-ink-800/50'"
            @mousedown.prevent="onSelect(item)"
            @mouseenter="highlightedIndex = i"
          >
            <div class="text-sm font-medium text-ink-700 dark:text-ink-200">{{ item.label }}</div>
            <div class="text-xs text-ink-400 dark:text-ink-500">{{ item.description }}</div>
          </li>
        </ul>
      </div>
    </template>
  </UModal>
</template>

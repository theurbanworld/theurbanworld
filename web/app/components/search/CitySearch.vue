<script setup lang="ts">
import { formatPopulation } from '~/utils/formatNumber'

const { searchTerm, results } = useCitySearch()

const open = ref(false)
const highlightedIndex = ref(-1)
const inputRef = ref<HTMLInputElement | null>(null)

const items = computed(() =>
  results.value.map(({ city }) => ({
    label: city.name,
    description: `${city.country} · ${formatPopulation(city.population)}`,
    value: city.id
  }))
)

function onSelect(item: { value: string }) {
  open.value = false
  searchTerm.value = ''
  highlightedIndex.value = -1
  navigateTo(`/city/${item.value}`)
}

function onFocus() {
  if (searchTerm.value.trim().length >= 2) open.value = true
}

function onBlur() {
  // Delay closing so click on item registers
  setTimeout(() => {
    open.value = false
  }, 150)
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value || !items.value.length) return

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
  } else if (e.key === 'Escape') {
    open.value = false
    inputRef.value?.blur()
  }
}

watch(searchTerm, (val) => {
  open.value = val.trim().length >= 2
})

// Auto-highlight the first result so Enter selects it immediately
watch(items, (list) => {
  highlightedIndex.value = list.length ? 0 : -1
})

// ⌘K / Ctrl+K focuses the search input
defineShortcuts({
  meta_k: () => {
    inputRef.value?.focus()
  }
})

// Platform-aware hint: ⌘K on macOS, CtrlK elsewhere
const { getKbdKey } = useKbd()
const shortcutHint = computed(() => `${getKbdKey('meta')}K`)
</script>

<template>
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
        class="w-full pl-9 pr-12 py-2 text-sm rounded-md
               bg-white dark:bg-ink-900
               border border-ink-200 dark:border-ink-700
               text-ink-700 dark:text-ink-200
               placeholder:text-ink-400 dark:placeholder:text-ink-500
               focus:outline-none focus:ring-2 focus:ring-ink-400/40 dark:focus:ring-ink-500/40
               transition"
        @focus="onFocus"
        @blur="onBlur"
        @keydown="onKeydown"
      >
      <UKbd
        :value="shortcutHint"
        class="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
      />
    </div>

    <ul
      v-if="open && items.length"
      class="absolute z-50 mt-1 w-full max-h-80 overflow-y-auto rounded-md
             bg-white dark:bg-ink-900
             border border-ink-200 dark:border-ink-700
             shadow-lg py-1"
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
        <div class="text-sm font-medium text-ink-700 dark:text-ink-200">
          {{ item.label }}
        </div>
        <div class="text-xs text-ink-400 dark:text-ink-500">
          {{ item.description }}
        </div>
      </li>
    </ul>
  </div>
</template>

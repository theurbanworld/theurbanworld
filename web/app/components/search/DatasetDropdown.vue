<script setup lang="ts">
/**
 * DatasetDropdown - Dataset selector in the search strip
 *
 * Replaces the former "Cities" button. Shows the active dataset
 * with a dropdown to switch between available datasets.
 * Each item includes an info link to its documentation page.
 */

import type { DropdownMenuItem } from '@nuxt/ui'

const { activeDataset, activeDatasetLabel, datasets, setDataset } = useDataset()
const { open: openInfoModal } = useInfoModal()

const items = computed<DropdownMenuItem[][]>(() => [
  datasets.map(dataset => ({
    label: `${dataset.name} ${dataset.version}`,
    icon: dataset.id === activeDataset.value.id ? 'i-lucide-check' : undefined,
    onSelect: () => setDataset(dataset.id),
    slot: 'dataset' as const,
    dataset
  }))
])

function handleInfoClick(event: Event, contentPath: string) {
  event.stopPropagation()
  openInfoModal(contentPath)
}
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ align: 'start', side: 'bottom' }"
    :modal="false"
    size="sm"
  >
    <UButton
      variant="ghost"
      color="neutral"
      size="sm"
      trailing-icon="i-lucide-chevron-down"
      class="cursor-pointer"
    >
      {{ activeDatasetLabel }}
    </UButton>

    <template #item-trailing="{ item }">
      <button
        v-if="(item as any).dataset"
        class="ml-2 p-0.5 rounded text-body/40 dark:text-cream/40
               hover:text-forest-700 dark:hover:text-forest-300
               transition-colors cursor-pointer"
        title="Dataset info"
        @click="handleInfoClick($event, (item as any).dataset.contentPath)"
      >
        <UIcon name="i-lucide-info" class="w-3.5 h-3.5" />
      </button>
    </template>
  </UDropdownMenu>
</template>

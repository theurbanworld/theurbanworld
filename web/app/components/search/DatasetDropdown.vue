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

const items = computed<DropdownMenuItem[][]>(() => [
  datasets.map(dataset => ({
    label: `${dataset.name} ${dataset.version}`,
    icon: dataset.id === activeDataset.value.id ? 'i-lucide-check' : undefined,
    onSelect: () => setDataset(dataset.id),
    slot: 'dataset' as const,
    dataset
  }))
])
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
      <NuxtLink
        v-if="(item as any).dataset"
        :to="(item as any).dataset.contentPath"
        class="ml-2 p-0.5 rounded text-body/40 dark:text-cream/40
               hover:text-forest-700 dark:hover:text-forest-300
               transition-colors"
        title="Dataset info"
        @click.stop
      >
        <UIcon name="i-lucide-info" class="w-3.5 h-3.5" />
      </NuxtLink>
    </template>
  </UDropdownMenu>
</template>

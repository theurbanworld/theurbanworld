<script setup lang="ts">
/**
 * DatasetPicker - Modal-based dataset selector
 *
 * Shows the active dataset name in the strip. Clicking opens a modal
 * with dataset cards showing descriptions and links to full documentation.
 */

const { activeDataset, activeDatasetLabel, datasets, setDataset } = useDataset()
const { open: openInfoModal } = useInfoModal()

const isOpen = ref(false)

function selectDataset(id: string) {
  setDataset(id)
  isOpen.value = false
}

function viewDatasetInfo(contentPath: string) {
  isOpen.value = false
  openInfoModal(contentPath)
}
</script>

<template>
  <UModal v-model:open="isOpen" title="Choose a dataset" description="Each dataset offers a different view of global urbanization.">
    <button
      class="flex items-center gap-1.5 py-1 px-2 rounded-md
             hover:bg-forest-100/50 dark:hover:bg-forest-900/30
             transition-colors cursor-pointer"
    >
      <span class="text-xs text-body/50 dark:text-cream/50">Dataset</span>
      <span class="text-sm font-medium text-body/70 dark:text-cream/70">
        {{ activeDatasetLabel }}
      </span>
    </button>

    <template #body>
      <div class="flex flex-col gap-3">
        <button
          v-for="dataset in datasets"
          :key="dataset.id"
          class="flex flex-col gap-2 p-4 rounded-lg border text-left transition-all cursor-pointer"
          :class="dataset.id === activeDataset.id
            ? 'border-forest-500 dark:border-forest-400 bg-forest-50/50 dark:bg-forest-950/30 ring-1 ring-forest-500/30'
            : 'border-forest-200/40 dark:border-forest-800/40 hover:border-forest-300 dark:hover:border-forest-700 hover:bg-forest-50/30 dark:hover:bg-forest-950/20'"
          @click="selectDataset(dataset.id)"
        >
          <!-- Header row -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="font-semibold text-forest-700 dark:text-forest-300">
                {{ dataset.name }}
              </span>
              <span class="text-xs font-mono px-1.5 py-0.5 rounded bg-forest-100/60 dark:bg-forest-900/40 text-body/60 dark:text-cream/60">
                {{ dataset.version }}
              </span>
            </div>
            <UIcon
              v-if="dataset.id === activeDataset.id"
              name="i-lucide-check"
              class="w-4 h-4 text-forest-600 dark:text-forest-400"
            />
          </div>

          <!-- Description -->
          <p class="text-sm text-body/60 dark:text-cream/60 leading-relaxed">
            {{ dataset.description }}
          </p>

          <!-- Info link -->
          <span
            class="text-xs text-forest-600 dark:text-forest-400 hover:underline inline-flex items-center gap-1"
            @click.stop="viewDatasetInfo(dataset.contentPath)"
          >
            Learn more
            <UIcon name="i-lucide-arrow-right" class="w-3 h-3" />
          </span>
        </button>
      </div>
    </template>
  </UModal>
</template>

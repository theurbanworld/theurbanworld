<script setup lang="ts">
/**
 * InfoModal — global modal for contextual source/methodology info
 *
 * Mounted once in app.vue (outside layouts). Opens when useInfoModal().open()
 * is called with a content path like '/data/source-ghsl'.
 */

const { activePath, isOpen, close } = useInfoModal()

const { data: content } = await useAsyncData(
  () => `info-modal-${activePath.value}`,
  () => {
    if (!activePath.value) return Promise.resolve(null)

    const collection = activePath.value.startsWith('/methodology') ? 'methodology' : 'data'
    return queryCollection(collection).path(activePath.value).first()
  },
  { watch: [activePath] }
)

const parentPage = computed(() => {
  if (!content.value) return null
  return (content.value as any).parentPage as string | undefined
})

const parentLabel = computed(() => {
  if (!parentPage.value) return ''
  return parentPage.value === '/data' ? 'Data page' : 'Methodology page'
})
</script>

<template>
  <UModal v-model:open="isOpen">
    <template #content>
      <div class="p-6 max-h-[80vh] overflow-y-auto">
        <ContentRenderer
          v-if="content"
          :value="content"
          class="prose prose-forest dark:prose-invert prose-sm max-w-none"
        />

        <div v-if="parentPage" class="mt-6 pt-4 border-t border-forest-200/40 dark:border-forest-800/40">
          <NuxtLink
            :to="parentPage"
            class="text-sm text-forest-600 dark:text-forest-400 hover:underline"
            @click="close"
          >
            Read more on the {{ parentLabel }}
          </NuxtLink>
        </div>
      </div>
    </template>
  </UModal>
</template>

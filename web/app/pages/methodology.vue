<script setup lang="ts">
definePageMeta({ layout: 'content' })

useSeoMeta({
  title: 'Methodology — The Urban World',
  description: 'Methodology behind The Urban World data processing and analysis.'
})

const { data: sections } = await useAsyncData('methodology-sections', () =>
  queryCollection('methodology').order('stem', 'ASC').all()
)
</script>

<template>
  <div>
    <template v-if="sections">
      <ContentRenderer
        v-for="section in sections"
        :key="section.stem"
        :value="section"
        class="prose prose-forest dark:prose-invert max-w-none"
      />
    </template>
  </div>
</template>

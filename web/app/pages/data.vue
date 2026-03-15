<script setup lang="ts">
definePageMeta({ layout: 'content' })

useSeoMeta({
  title: 'Data — The Urban World',
  description: 'Data sources powering The Urban World observatory.'
})

const { data: sections } = await useAsyncData('data-sections', () =>
  queryCollection('data').order('stem', 'ASC').all()
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

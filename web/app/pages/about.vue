<script setup lang="ts">
definePageMeta({ layout: 'content' })

useSeoMeta({
  title: 'About — The Urban World',
  description: 'About The Urban World, an observatory of urban complexity.'
})

const { data: page } = await useAsyncData('about', () =>
  queryCollection('pages').path('/about').first()
)
</script>

<template>
  <div>
    <ContentRenderer v-if="page" :value="page" class="prose prose-forest dark:prose-invert max-w-none" />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'content' })

useSeoMeta({
  title: 'Methodology — The Urban World',
  description: 'Methodology behind The Urban World data processing and analysis.'
})

const { data: sections } = await useAsyncData('methodology-sections', () =>
  queryCollection('methodology').order('stem', 'ASC').all()
)

// Each section is authored as a standalone document leading with its own <h1>.
// Demote them to <h2> so the page keeps a single, page-level <h1>, and namespace
// their heading ids by stem so repeated headings don't collide across sections.
const renderedSections = computed(() =>
  (sections.value ?? []).map(section => ({
    ...section,
    body: shiftHeadings(prefixHeadingIds(section.body, section.stem))
  }))
)

const tocLinks = computed(() => buildToc(...renderedSections.value.map(s => s.body)))
</script>

<template>
  <ContentTocLayout :links="tocLinks">
    <div class="prose prose-forest dark:prose-invert max-w-none">
      <h1>Methodology</h1>
    </div>
    <ContentRenderer
      v-for="section in renderedSections"
      :key="section.stem"
      :value="section"
      class="prose prose-forest dark:prose-invert max-w-none"
    />
  </ContentTocLayout>
</template>

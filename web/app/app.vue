<script setup lang="ts">
/**
 * Root app shell
 *
 * Holds persistent chrome (header, footer, modal) and delegates
 * page-specific layout to <NuxtLayout>.
 */

useHead({
  title: 'The Urban World — an observatory of urban complexity',
  link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]
})

useSeoMeta({
  description: 'The Urban World tells the story of global urbanization through data, making visible the shape, density, and growth of cities over time.',
  ogTitle: 'The Urban World — an observatory of urban complexity',
  ogDescription: 'The Urban World tells the story of global urbanization through data, making visible the shape, density, and growth of cities over time.'
})

defineOgImage('Default')

// Site-wide structured data
useSchemaOrg([
  defineWebSite({
    name: 'The Urban World',
    description: 'An observatory of urban complexity — telling the story of global urbanization through data.',
    inLanguage: 'en'
  })
])

// Initialize dark mode on mount
const { initializeDarkMode } = useDarkMode()

onMounted(() => {
  initializeDarkMode()
})
</script>

<template>
  <UApp>
    <div class="flex flex-col h-screen overflow-hidden">
      <AppHeader />

      <NuxtLayout>
        <NuxtPage />
      </NuxtLayout>
    </div>

    <!-- Global modals — outside layouts so they're always available -->
    <InfoModal />
    <FeedbackModal />
  </UApp>
</template>

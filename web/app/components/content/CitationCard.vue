<script setup lang="ts">
/**
 * CitationCard — MDC component for rendering academic citations
 *
 * Usage in markdown:
 * ::citation-card{author="Bertaud, A." year="2018" title="Order without Design" url="https://..."}
 * ::
 */

defineProps<{
  author: string
  year: string
  title: string
  url?: string
}>()
</script>

<template>
  <div class="my-4 px-4 py-3 rounded-lg border border-ink-200/40 dark:border-ink-800/40 bg-ink-50/30 dark:bg-ink-950/20">
    <p class="text-sm text-body/80 dark:text-cream/80">
      <span class="font-medium">{{ author }}</span>
      <span class="text-body/60 dark:text-cream/60"> ({{ year }})</span>.
      <template v-if="url">
        <a
          :href="url"
          target="_blank"
          rel="noopener"
          class="italic underline hover:text-ink-600 dark:hover:text-ink-400 transition-colors"
        >{{ title }}</a>.
      </template>
      <template v-else>
        <span class="italic">{{ title }}</span>.
      </template>
    </p>
  </div>
</template>

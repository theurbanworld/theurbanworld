<script setup lang="ts">
/**
 * Two-column reading layout for long-form content pages.
 *
 * Renders a sticky left-hand table of contents (Nuxt UI's <UContentToc>)
 * alongside the page content. On mobile the TOC collapses into an accordion
 * above the content. When a page has no sub-headings, the content is shown
 * full-width with no sidebar.
 */
import type { TocItem } from '~/utils/contentToc'

const props = defineProps<{
  links?: TocItem[]
}>()

function countItems(items: TocItem[] = []): number {
  return items.reduce((total, item) => total + 1 + countItems(item.children), 0)
}

// A single-heading page (e.g. just the page title) doesn't warrant a TOC —
// only show the sidebar once there's something worth navigating between.
const showToc = computed(() => countItems(props.links) >= 2)

// The page chrome keeps the window fixed and scrolls content inside a nested
// container, so the router's default (window-based) hash scroll is a no-op.
// Scroll the heading into view ourselves when a TOC link is activated.
function scrollToHeading(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <!-- Default (stretch) alignment is intentional: it lets the <aside> grow to
       the full height of the content column, which is what gives the sticky
       TOC inside it the vertical range to travel as the reader scrolls. -->
  <div
    v-if="showToc"
    class="lg:flex lg:justify-center lg:gap-12"
  >
    <aside class="mb-10 lg:mb-0 lg:order-first lg:w-56 lg:shrink-0">
      <UContentToc
        :links="links"
        title="On this page"
        highlight
        color="primary"
        class="lg:sticky lg:top-2 lg:max-h-[calc(100vh-9rem)] lg:overflow-y-auto lg:bg-transparent"
        @move="scrollToHeading"
      />
    </aside>

    <div class="min-w-0 lg:w-full lg:max-w-3xl">
      <slot />
    </div>
  </div>

  <div
    v-else
    class="mx-auto max-w-3xl"
  >
    <slot />
  </div>
</template>

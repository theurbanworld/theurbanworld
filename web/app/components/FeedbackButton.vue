<script setup lang="ts">
/**
 * FeedbackButton — persistent desktop entry point for the feedback widget.
 *
 * Fixed at the bottom center (clear of the map's bottom-right attribution),
 * visible on every route (mounted in app.vue), hidden on mobile where the nav
 * drawer carries the entry point instead. Fully persistent — no
 * hide/collapse-on-scroll (confirmed scope). Translucent so the map reads
 * through it; hover shifts the shade rather than going fully opaque.
 */

const { open } = useFeedback()
</script>

<template>
  <button
    type="button"
    aria-label="Send feedback"
    class="max-sm:hidden fixed bottom-5 left-1/2 -translate-x-1/2 z-40
           inline-flex items-center gap-2 px-4 py-2.5 rounded-full cursor-pointer
           text-sm font-medium text-white shadow-lg backdrop-blur-sm
           bg-forest-600/85 hover:bg-forest-700/85
           dark:bg-forest-500/85 dark:hover:bg-forest-600/85
           transition-colors"
    @click="open"
  >
    <UIcon
      name="i-lucide-message-square"
      class="w-4 h-4"
    />
    Feedback
  </button>
</template>

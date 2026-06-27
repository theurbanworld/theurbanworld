<script setup lang="ts">
/**
 * FeedbackButton — persistent desktop entry point for the feedback widget.
 *
 * Fixed in the bottom-right corner, visible on every route (mounted in
 * app.vue), hidden on mobile where the nav drawer carries the entry point
 * instead. Fully persistent — no hide/collapse-on-scroll (confirmed scope).
 */

const { open } = useFeedback()
</script>

<template>
  <UButton
    icon="i-lucide-message-square"
    color="primary"
    size="lg"
    class="max-sm:hidden fixed bottom-5 right-5 z-40 rounded-full shadow-lg"
    aria-label="Send feedback"
    @click="open"
  >
    Feedback
  </UButton>
</template>

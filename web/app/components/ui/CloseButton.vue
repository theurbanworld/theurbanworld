<script setup lang="ts">
/**
 * CloseButton — shared dismiss button with a subtle ghost background.
 *
 * Used for sidebar panels, page headers, and modal close affordances so the
 * "X" looks consistent everywhere. Renders a single <button> root, so it can
 * be dropped into Nuxt UI's `#close` slot (DialogClose `as-child`) or wired up
 * with a plain `@click` handler.
 */

withDefaults(
  defineProps<{
    /** Accessible label describing what gets closed */
    ariaLabel?: string
  }>(),
  { ariaLabel: 'Close' }
)
</script>

<template>
  <button
    type="button"
    :aria-label="ariaLabel"
    class="shrink-0 flex items-center justify-center p-1 rounded-md cursor-pointer
           text-body/50 dark:text-cream/50
           bg-ink-100/50 dark:bg-ink-900/30
           hover:bg-ink-200/60 dark:hover:bg-ink-800/40
           hover:text-ink-700 dark:hover:text-ink-300
           transition-colors"
  >
    <UIcon
      name="i-lucide-x"
      class="w-4 h-4 block"
    />
  </button>
</template>

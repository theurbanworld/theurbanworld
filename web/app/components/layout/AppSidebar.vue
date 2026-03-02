<script setup lang="ts">
/**
 * AppSidebar - True sidebar that pushes map content
 *
 * A full-height left sidebar flush with the header and viewport edges.
 * Always rendered in the DOM; toggles between w-80 and w-0 with a
 * CSS width transition for smooth open/close animation.
 * On mobile (max-sm), overlays as a full-screen panel instead.
 */

interface Props {
  /** Controls sidebar visibility */
  open: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  /** Emitted when close button is clicked */
  close: []
}>()

function handleClose() {
  emit('close')
}
</script>

<template>
  <aside
    data-testid="app-sidebar"
    class="flex-shrink-0 overflow-hidden
           transition-[width] duration-300 ease-in-out
           bg-parchment
           border-r border-forest-200/40 dark:border-forest-800/40
           max-sm:fixed max-sm:inset-0 max-sm:z-200 max-sm:border-r-0
           max-sm:transition-transform max-sm:duration-300 max-sm:ease-in-out"
    :class="[
      open ? 'w-80 max-sm:translate-x-0' : 'w-0 max-sm:-translate-x-full'
    ]"
  >
    <!-- Inner wrapper with fixed width to prevent content reflow -->
    <div class="w-80 min-w-80 h-full flex flex-col">
      <!-- Content slot -->
      <div
        data-testid="sidebar-content"
        class="flex-1 overflow-y-auto p-5 pt-16"
      >
        <slot />
      </div>
    </div>
  </aside>
</template>

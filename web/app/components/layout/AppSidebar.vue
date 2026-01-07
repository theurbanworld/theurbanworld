<script setup lang="ts">
/**
 * AppSidebar - Generic reusable sidebar component
 *
 * A full-height left sidebar that slides in from the left edge.
 * Can be used for city info panels, search results, or other content.
 * Fixed position that overlays the map without pushing content.
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
  <Transition name="sidebar-slide">
    <aside
      v-if="open"
      data-testid="app-sidebar"
      class="absolute left-4 top-24 bottom-4 z-200 w-80
             max-sm:left-2 max-sm:top-16 max-sm:bottom-2 max-sm:w-[calc(100%-1rem)]
             bg-parchment/95 dark:bg-espresso/95 backdrop-blur-sm
             shadow-lg rounded-xl
             flex flex-col overflow-hidden"
    >
      <!-- Close button -->
      <button
        data-testid="sidebar-close-button"
        class="absolute top-4 right-4 z-10
               p-2 rounded-lg
               text-body/70 dark:text-cream/70
               hover:bg-forest-100/50 dark:hover:bg-forest-900/30
               hover:text-forest-700 dark:hover:text-forest-300
               transition-colors"
        aria-label="Close sidebar"
        @click="handleClose"
      >
        <UIcon name="i-lucide-x" class="w-5 h-5" />
      </button>

      <!-- Content slot -->
      <div
        data-testid="sidebar-content"
        class="flex-1 overflow-y-auto p-6 pt-14"
      >
        <slot />
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
/* Slide-in animation for sidebar */
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 0.3s ease;
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(-100%);
}

.sidebar-slide-enter-to,
.sidebar-slide-leave-from {
  transform: translateX(0);
}
</style>

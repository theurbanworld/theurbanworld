<script setup lang="ts">
/**
 * AppSidebar - Persistent left sidebar that pushes map content
 *
 * Always visible at w-80 on desktop with a header slot (non-scrollable)
 * and a default content slot (scrollable).
 * On mobile (max-sm), overlays as a full-screen panel controlled by `open` prop.
 */

interface Props {
  /** Controls sidebar visibility on mobile */
  open?: boolean
}

withDefaults(defineProps<Props>(), { open: true })
</script>

<template>
  <aside
    data-testid="app-sidebar"
    class="w-80 shrink-0 bg-parchment
           border-r border-ink-200/40 dark:border-ink-800/40
           max-sm:fixed max-sm:inset-0 max-sm:z-200 max-sm:border-r-0
           max-sm:transition-transform max-sm:duration-300 max-sm:ease-in-out"
    :class="[
      open ? 'max-sm:translate-x-0' : 'max-sm:-translate-x-full'
    ]"
  >
    <div class="w-80 min-w-80 h-full flex flex-col">
      <!-- Non-scrollable header -->
      <slot name="header" />
      <!-- Scrollable content -->
      <div
        data-testid="sidebar-content"
        class="flex-1 overflow-y-auto"
      >
        <slot />
      </div>
    </div>
  </aside>
</template>

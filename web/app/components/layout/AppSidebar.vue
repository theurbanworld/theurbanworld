<script setup lang="ts">
/**
 * AppSidebar - Left sidebar (desktop) / bottom drawer (mobile)
 *
 * Desktop: Always visible at w-96, pushes map content.
 * Mobile: UDrawer from bottom with snap points, controlled via useMobileSidebar.
 */

const isMobile = useIsMobile()
const { isOpen: mobileOpen } = useMobileSidebar()
</script>

<template>
  <!-- Desktop sidebar -->
  <aside
    v-if="!isMobile"
    data-testid="app-sidebar"
    class="w-96 shrink-0 bg-parchment
           border-r border-ink-200/40 dark:border-ink-800/40"
  >
    <div class="w-96 min-w-96 h-full flex flex-col">
      <slot name="header" />
      <div
        data-testid="sidebar-content"
        class="flex-1 overflow-y-auto"
      >
        <slot />
      </div>
    </div>
  </aside>

  <!-- Mobile bottom drawer -->
  <UDrawer
    v-else
    v-model:open="mobileOpen"
    direction="bottom"
    :handle="true"
    handle-only
    :overlay="true"
    :snap-points="[0.5, 1]"
    :active-snap-point="0.5"
  >
    <template #default>
      <span />
    </template>
    <template #content>
      <div class="flex flex-col h-full max-h-[calc(100dvh-4rem)]">
        <slot name="header" />
        <div class="flex-1 overflow-y-auto">
          <slot />
        </div>
      </div>
    </template>
  </UDrawer>
</template>

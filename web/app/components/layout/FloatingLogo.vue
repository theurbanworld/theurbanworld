<script setup lang="ts">
/**
 * FloatingLogo - Floating logo panel positioned at top-left
 *
 * Displays the app logo floating above the map, with consistent
 * styling matching other floating panels (GlobalContextPanel, ZoomSlider).
 * Positioned above the AppSidebar when it's open.
 */
</script>

<template>
  <div
    class="absolute left-4 top-4 z-300 p-3 rounded-xl shadow-lg
           bg-parchment/95 backdrop-blur-sm
           max-sm:left-2 max-sm:top-2"
  >
    <AppLogo />
  </div>
</template>

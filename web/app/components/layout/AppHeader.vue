<script setup lang="ts">
/**
 * AppHeader - Full-width header bar with centered logo
 *
 * Sits above the map viewport. Centers AppLogo with
 * DarkModeToggle absolute-positioned to the right.
 */
</script>

<template>
  <header
    class="relative flex items-center justify-center px-5 py-3
           bg-parchment dark:bg-espresso
           border-b border-forest-200/40 dark:border-forest-800/40
           max-sm:px-3 max-sm:py-2"
  >
    <AppLogo />
    <DarkModeToggle class="absolute right-5 max-sm:right-3" />
  </header>
</template>

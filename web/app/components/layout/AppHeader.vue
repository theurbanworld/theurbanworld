<script setup lang="ts">
/**
 * AppHeader - Full-width header bar with logo, centered title, and controls
 *
 * Top row: SVG logo (left), AppLogo title (centered), DarkModeToggle (right)
 * Bottom row: CitySearch (centered)
 */
</script>

<template>
  <header
    class="flex flex-col items-center gap-2 px-5 py-3
           bg-parchment dark:bg-espresso
           border-b border-forest-200/40 dark:border-forest-800/40
           max-sm:px-3 max-sm:py-2"
  >
    <div class="grid grid-cols-[1fr_auto_1fr] items-center w-full gap-3">
      <img
        src="/logo.svg"
        alt="The Urban World"
        class="h-8 max-sm:h-6 dark:invert"
      />
      <AppLogo />
      <div class="flex justify-end">
        <DarkModeToggle />
      </div>
    </div>
    <CitySearch class="w-full max-w-sm" />
  </header>
</template>

<template>
  <UApp>
    <div class="flex flex-col h-screen overflow-hidden">
      <UHeader :style="{ '--ui-header-height': '5rem' }">
        <template #title>
          <AppLogo />
        </template>

        <template #right>
          <DarkModeToggle />
        </template>
      </UHeader>

      <UMain class="flex-1 !min-h-0 relative overflow-hidden">
        <NuxtPage />
      </UMain>

      <UFooter>
        <template #left>
          <p class="text-muted text-sm">
            Urban World
          </p>
        </template>
      </UFooter>
    </div>
  </UApp>
</template>

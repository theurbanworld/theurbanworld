<template>
  <UApp>
    <div class="app-layout">
      <UHeader>
        <template #title>
          <AppLogo />
        </template>
      </UHeader>

      <UMain class="app-main">
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

<style>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* Override UMain's default min-height to use flex-1 instead */
.app-main {
  flex: 1;
  min-height: 0 !important;
  position: relative;
  overflow: hidden;
}
</style>

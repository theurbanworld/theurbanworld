<template>
  <div class="app-logo">
    <div class="logo-main">
      <UIcon
        name="i-lucide-globe"
        class="logo-icon"
      />
      <span class="logo-title">The Urban World</span>
    </div>
    <div class="logo-subtitle">
      an observatory of urban complexity
    </div>
  </div>
</template>

<style scoped>
.app-logo {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.logo-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logo-icon {
  width: 1.75rem;
  height: 1.75rem;
  color: var(--color-forest-500, #6A8F5E);
  flex-shrink: 0;
}

.logo-title {
  font-family: var(--font-family-serif, ui-serif, Georgia, serif);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--color-espresso, #3D352C);
}

.logo-subtitle {
  font-family: var(--font-family-sans, ui-sans-serif, system-ui, sans-serif);
  font-size: 0.875rem;
  font-weight: 300;
  letter-spacing: 0.02em;
  color: var(--color-warm-gray-600, #6B5E54);
  padding-left: 2.25rem;
}

/* Dark mode styles */
:global(.dark) .logo-icon {
  color: var(--color-forest-400, #8FAD85);
}

:global(.dark) .logo-title {
  color: var(--color-density-1, #F7F3E8);
}

:global(.dark) .logo-subtitle {
  color: var(--color-warm-gray-400, #A89E94);
}
</style>

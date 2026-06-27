<script setup lang="ts">
/**
 * AppHeader - Full-width header bar
 *
 * Desktop: [Logo + Title] | [Search] | [Nav links]
 * Mobile:  [Logo + Title] | [Hamburger]  then  [Search full width]
 */

const navLinks = [
  { to: '/about', label: 'About' },
  { to: '/data', label: 'Data' },
  { to: '/methodology', label: 'Methodology' }
]

const navDrawerOpen = ref(false)
const route = useRoute()
</script>

<template>
  <header
    class="bg-parchment border-b border-ink-200/40 dark:border-ink-800/40
           px-5 py-3 max-sm:px-3 max-sm:py-2"
  >
    <!-- Desktop: 3-column grid -->
    <div class="max-sm:hidden grid grid-cols-[auto_1fr_auto] items-center w-full gap-3">
      <NuxtLink
        to="/"
        class="flex items-center gap-3"
      >
        <svg
          class="h-6 text-ink-700 dark:text-ink-300"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="8 104 440 336"
          aria-label="The Urban World"
        >
          <g transform="matrix(0.435873 0 0 0.435547 6.10352e-05 0)">
            <path
              fill="currentColor"
              d="M466.766 644.743C476.322 645.019 488.633 646.414 498.247 647.678C556.481 655.331 604.311 676.412 645.813 718.146C728.364 801.158 717.502 896.677 716.624 1004.55C713.451 1005.14 699.23 1004.92 695.029 1004.91L649.997 1004.88L466.244 1004.85L466.766 644.743Z"
            />
            <path
              fill="currentColor"
              d="M324.445 481.334L442.509 481.011L441.423 1004.66L425.996 1004.76C386.986 1005.05 347.975 1005.06 308.965 1004.78L309.096 481.493L324.445 481.334Z"
            />
            <path
              fill="currentColor"
              d="M724.988 481.521L844.342 481.53L844.322 832.715L844.287 949.267L844.242 985.604C844.238 990.102 844.537 999.352 844.167 1003.41L843.272 1004.1C829.365 1005.33 813.371 1005.21 799.373 1005.19C779.511 1005.17 759.651 1004.96 739.793 1004.58L739.631 919.648C739.44 899.02 738.906 878.16 737.31 857.578C735.738 837.31 726.227 816.162 725.466 796.101C725.026 784.494 725.067 771.55 724.948 759.879L724.716 675.113C724.371 610.583 724.461 546.051 724.988 481.521Z"
            />
            <path
              fill="currentColor"
              d="M798.524 293.25C814.298 293.231 830.071 293.336 845.843 293.565C845.242 347.531 845.898 402.57 845.813 456.655L700.954 456.746C700.085 554.041 699.942 651.34 700.527 748.637C696.506 744.566 690.794 736.033 687.197 730.993C682.737 724.635 677.978 718.493 672.937 712.586C650.98 686.227 619.634 666.203 590.065 649.49L589.894 549.415C589.593 484.917 586.445 431.357 625.866 376.098C662.688 324.482 714.067 299.936 776.472 294.029C783.68 293.346 791.22 293.388 798.524 293.25Z"
            />
            <path
              fill="currentColor"
              d="M206.036 244.529L351.865 244.69C382.749 244.808 413.633 244.76 444.516 244.547L444.337 456.136L444.083 456.564C442.443 457.445 229.443 456.722 206.15 456.723L206.095 330.946C206.044 302.266 205.733 273.18 206.036 244.529Z"
            />
            <path
              fill="currentColor"
              d="M22.7661 696.491L183.064 696.466L182.236 1004.21C132.617 1007.53 73.48 1005.1 22.6919 1004.55L22.7661 696.491Z"
            />
            <path
              fill="currentColor"
              d="M881.945 696.785C929.401 696.136 977.623 696.499 1025.13 696.441L1024.96 1004.81L1010.5 1004.82L868.138 1004.86L868.26 696.944L881.945 696.785Z"
            />
            <path
              fill="currentColor"
              d="M206.987 481.107L283.765 481.156C285.117 655.643 285.141 830.137 283.837 1004.62C279.162 1005.16 263.664 1004.79 258.37 1004.79L206.71 1004.75L206.987 481.107Z"
            />
            <path
              fill="currentColor"
              d="M179.066 482.123C180.075 482.141 179.573 482.063 180.547 482.694C182.902 490.556 183.465 530.768 183.561 541.072C184 584.988 183.697 628.909 182.652 672.815L28.2562 672.341C22.169 671.231 22.4531 665.726 23.0515 660.805C26.5171 632.305 33.7566 606.108 47.5477 580.794C74.9456 530.504 124.642 497.587 179.066 482.123Z"
            />
            <path
              fill="currentColor"
              d="M868.107 482.397C902.532 488.874 934.419 504.974 960.072 528.832C1000.77 566.571 1022.83 617.424 1024.88 672.706C1006.19 673.035 986.789 672.688 968.031 672.647L868.132 672.534L868.107 482.397Z"
            />
          </g>
        </svg>
        <AppLogo />
      </NuxtLink>
      <CitySearch class="w-full max-w-lg mx-auto" />
      <nav class="flex justify-end items-center gap-4">
        <NuxtLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="text-sm font-medium transition-colors"
          active-class="text-ink-700 dark:text-ink-300"
          :class="route.path === link.to
            ? ''
            : 'text-body/60 dark:text-cream/60 hover:text-ink-600 dark:hover:text-ink-400'"
        >
          {{ link.label }}
        </NuxtLink>
        <DarkModeToggle />
      </nav>
    </div>

    <!-- Mobile: stacked rows -->
    <div class="sm:hidden">
      <!-- Row 1: Logo + title | hamburger -->
      <div class="flex items-center justify-between">
        <NuxtLink
          to="/"
          class="flex items-center gap-2"
        >
          <svg
            class="h-5 text-ink-700 dark:text-ink-300"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="8 104 440 336"
            aria-label="The Urban World"
          >
            <g transform="matrix(0.435873 0 0 0.435547 6.10352e-05 0)">
              <path
                fill="currentColor"
                d="M466.766 644.743C476.322 645.019 488.633 646.414 498.247 647.678C556.481 655.331 604.311 676.412 645.813 718.146C728.364 801.158 717.502 896.677 716.624 1004.55C713.451 1005.14 699.23 1004.92 695.029 1004.91L649.997 1004.88L466.244 1004.85L466.766 644.743Z"
              />
              <path
                fill="currentColor"
                d="M324.445 481.334L442.509 481.011L441.423 1004.66L425.996 1004.76C386.986 1005.05 347.975 1005.06 308.965 1004.78L309.096 481.493L324.445 481.334Z"
              />
              <path
                fill="currentColor"
                d="M724.988 481.521L844.342 481.53L844.322 832.715L844.287 949.267L844.242 985.604C844.238 990.102 844.537 999.352 844.167 1003.41L843.272 1004.1C829.365 1005.33 813.371 1005.21 799.373 1005.19C779.511 1005.17 759.651 1004.96 739.793 1004.58L739.631 919.648C739.44 899.02 738.906 878.16 737.31 857.578C735.738 837.31 726.227 816.162 725.466 796.101C725.026 784.494 725.067 771.55 724.948 759.879L724.716 675.113C724.371 610.583 724.461 546.051 724.988 481.521Z"
              />
              <path
                fill="currentColor"
                d="M798.524 293.25C814.298 293.231 830.071 293.336 845.843 293.565C845.242 347.531 845.898 402.57 845.813 456.655L700.954 456.746C700.085 554.041 699.942 651.34 700.527 748.637C696.506 744.566 690.794 736.033 687.197 730.993C682.737 724.635 677.978 718.493 672.937 712.586C650.98 686.227 619.634 666.203 590.065 649.49L589.894 549.415C589.593 484.917 586.445 431.357 625.866 376.098C662.688 324.482 714.067 299.936 776.472 294.029C783.68 293.346 791.22 293.388 798.524 293.25Z"
              />
              <path
                fill="currentColor"
                d="M206.036 244.529L351.865 244.69C382.749 244.808 413.633 244.76 444.516 244.547L444.337 456.136L444.083 456.564C442.443 457.445 229.443 456.722 206.15 456.723L206.095 330.946C206.044 302.266 205.733 273.18 206.036 244.529Z"
              />
              <path
                fill="currentColor"
                d="M22.7661 696.491L183.064 696.466L182.236 1004.21C132.617 1007.53 73.48 1005.1 22.6919 1004.55L22.7661 696.491Z"
              />
              <path
                fill="currentColor"
                d="M881.945 696.785C929.401 696.136 977.623 696.499 1025.13 696.441L1024.96 1004.81L1010.5 1004.82L868.138 1004.86L868.26 696.944L881.945 696.785Z"
              />
              <path
                fill="currentColor"
                d="M206.987 481.107L283.765 481.156C285.117 655.643 285.141 830.137 283.837 1004.62C279.162 1005.16 263.664 1004.79 258.37 1004.79L206.71 1004.75L206.987 481.107Z"
              />
              <path
                fill="currentColor"
                d="M179.066 482.123C180.075 482.141 179.573 482.063 180.547 482.694C182.902 490.556 183.465 530.768 183.561 541.072C184 584.988 183.697 628.909 182.652 672.815L28.2562 672.341C22.169 671.231 22.4531 665.726 23.0515 660.805C26.5171 632.305 33.7566 606.108 47.5477 580.794C74.9456 530.504 124.642 497.587 179.066 482.123Z"
              />
              <path
                fill="currentColor"
                d="M868.107 482.397C902.532 488.874 934.419 504.974 960.072 528.832C1000.77 566.571 1022.83 617.424 1024.88 672.706C1006.19 673.035 986.789 672.688 968.031 672.647L868.132 672.534L868.107 482.397Z"
              />
            </g>
          </svg>
          <AppLogo />
        </NuxtLink>
        <UButton
          icon="i-lucide-menu"
          variant="ghost"
          color="neutral"
          size="sm"
          aria-label="Open menu"
          @click="navDrawerOpen = true"
        />
      </div>
      <!-- Row 2: Search bar full width -->
      <div class="mt-2">
        <CitySearch class="w-full" />
      </div>
    </div>
  </header>

  <!-- Mobile nav drawer (right side) -->
  <UDrawer
    v-model:open="navDrawerOpen"
    direction="right"
    title="Menu"
  >
    <template #default>
      <span />
    </template>
    <template #body>
      <nav class="flex flex-col gap-1">
        <NuxtLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="px-3 py-2.5 rounded-md text-base font-medium transition-colors"
          active-class="text-ink-700 dark:text-ink-300 bg-ink-100/50 dark:bg-ink-900/30"
          :class="route.path === link.to
            ? ''
            : 'text-body/70 dark:text-cream/70 hover:text-ink-600 dark:hover:text-ink-400 hover:bg-ink-50 dark:hover:bg-ink-900/20'"
          @click="navDrawerOpen = false"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>
      <div class="mt-6 pt-4 border-t border-ink-200/40 dark:border-ink-800/40 px-3">
        <DarkModeToggle />
      </div>
    </template>
  </UDrawer>
</template>

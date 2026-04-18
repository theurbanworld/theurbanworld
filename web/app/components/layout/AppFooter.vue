<template>
  <footer
    class="relative flex items-center justify-center px-5 py-1.5
           bg-parchment
           border-t border-ink-200/40 dark:border-ink-800/40"
  >
    <span class="font-sans text-xs tracking-wide text-body/60 dark:text-dark-body/60">
      an observatory of urban complexity
      <span class="mx-1">&middot;</span>
      by <a
        href="https://pichot.us"
        target="_blank"
        rel="noopener"
        class="underline hover:text-ink-600 dark:hover:text-ink-400 transition-colors"
      >Jonathan Pichot</a>
      <span class="mx-1">&middot;</span>
      <a
        href="https://github.com/theurbanworld/theurbanworld"
        target="_blank"
        rel="noopener"
        aria-label="GitHub"
        class="hover:text-ink-600 dark:hover:text-ink-400 transition-colors"
      ><UIcon
        name="i-simple-icons-github"
        class="w-3.5 h-3.5 align-text-bottom"
      /></a>
      <a
        href="https://bsky.app/profile/pichot.bsky.social"
        target="_blank"
        rel="noopener"
        aria-label="Bluesky"
        class="hover:text-ink-600 dark:hover:text-ink-400 transition-colors ml-1"
      ><UIcon
        name="i-simple-icons-bluesky"
        class="w-3.5 h-3.5 align-text-bottom"
      /></a>
    </span>
    <DarkModeToggle class="absolute right-5 max-sm:hidden" />
  </footer>
</template>

<script setup lang="ts">
const props = defineProps<{
  type: 'article' | 'video' | 'book' | 'podcast' | 'film'
  title: string
  url?: string
  description?: string
  author?: string
  channel?: string
  show?: string
  director?: string
  date?: string
  year?: string
  duration?: string
}>()

const iconMap: Record<string, string> = {
  article: 'i-lucide-newspaper',
  video: 'i-lucide-play-circle',
  book: 'i-lucide-book-open',
  podcast: 'i-lucide-headphones',
  film: 'i-lucide-film'
}

const icon = computed(() => iconMap[props.type])

const metadata = computed(() => {
  const parts: string[] = []
  switch (props.type) {
    case 'article':
      if (props.author) parts.push(props.author)
      if (props.date) parts.push(props.date)
      break
    case 'video':
      if (props.channel) parts.push(props.channel)
      if (props.date) parts.push(props.date)
      if (props.duration) parts.push(props.duration)
      break
    case 'book':
      if (props.author) parts.push(props.author)
      if (props.year) parts.push(props.year)
      break
    case 'podcast':
      if (props.show) parts.push(props.show)
      if (props.date) parts.push(props.date)
      if (props.duration) parts.push(props.duration)
      break
    case 'film':
      if (props.director) parts.push(props.director)
      if (props.year) parts.push(props.year)
      break
  }
  return parts.join(' \u00b7 ')
})
</script>

<template>
  <div class="px-4 py-3 rounded-lg border border-ink-200/40 dark:border-ink-800/40 bg-ink-50/30 dark:bg-ink-950/20">
    <div class="flex gap-3">
      <UIcon
        :name="icon"
        class="w-4 h-4 mt-0.5 shrink-0 text-ink-500 dark:text-ink-400"
      />
      <div class="min-w-0">
        <component
          :is="url ? 'a' : 'span'"
          :href="url"
          :target="url ? '_blank' : undefined"
          :rel="url ? 'noopener' : undefined"
          class="text-sm font-medium text-body dark:text-cream"
          :class="url && 'underline hover:text-ink-600 dark:hover:text-ink-400 transition-colors'"
        >
          {{ title }}
        </component>
        <p
          v-if="metadata"
          class="text-xs text-body/60 dark:text-cream/60 mt-0.5"
        >
          {{ metadata }}
        </p>
        <p
          v-if="description"
          class="text-xs text-body/50 dark:text-cream/50 mt-1"
        >
          {{ description }}
        </p>
      </div>
    </div>
  </div>
</template>

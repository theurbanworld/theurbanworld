<script setup lang="ts">
const props = defineProps<{
  cityId: string
}>()

const { data: mediaItems } = await useAsyncData(
  () => `city-media-${props.cityId}`,
  () => queryCollection('media').all(),
  { watch: [() => props.cityId] }
)

const groupedMedia = computed(() => {
  if (!mediaItems.value) return null

  const filtered = mediaItems.value.filter(item => item.cityIds?.includes(props.cityId))
  if (filtered.length === 0) return null

  const typeOrder = ['article', 'video', 'book', 'podcast', 'film'] as const
  const labelMap: Record<string, string> = {
    article: 'Articles',
    video: 'Videos',
    book: 'Books',
    podcast: 'Podcasts',
    film: 'Films'
  }

  const groups: { label: string; items: typeof filtered }[] = []
  for (const type of typeOrder) {
    const items = filtered.filter(item => item.type === type)
    if (items.length > 0) {
      groups.push({ label: labelMap[type], items })
    }
  }
  return groups
})
</script>

<template>
  <div v-if="groupedMedia" class="border-t border-border/30 dark:border-border/20 pt-4">
    <div v-for="group in groupedMedia" :key="group.label" class="mb-4 last:mb-0">
      <h2 class="text-sm font-medium text-forest-700 dark:text-forest-300 mb-2">
        {{ group.label }}
      </h2>
      <div class="flex flex-col gap-2">
        <MediaCard
          v-for="item in group.items"
          :key="item.id"
          :type="item.type"
          :title="item.title"
          :url="item.url"
          :description="item.description"
          :author="item.author"
          :channel="item.channel"
          :show="item.show"
          :director="item.director"
          :date="item.date"
          :year="item.year"
          :duration="item.duration"
        />
      </div>
    </div>
  </div>
</template>

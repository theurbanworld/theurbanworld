<script setup lang="ts">
/**
 * ChartToggle - Switches between two chart views with text tab labels
 *
 * Shows small text labels (e.g., "over time" / "vs all cities") above the chart area.
 * Only the active chart is rendered.
 */

const props = withDefaults(defineProps<{
  labelA?: string
  labelB?: string
}>(), {
  labelA: 'over time',
  labelB: 'vs all cities',
})

const active = ref<'a' | 'b'>('a')
</script>

<template>
  <div class="mt-1">
    <div class="flex gap-2 mb-0.5">
      <button
        class="text-[10px] font-mono transition-colors cursor-pointer"
        :class="active === 'a'
          ? 'text-ink-600 dark:text-ink-400'
          : 'text-body/30 dark:text-cream/30 hover:text-body/50 dark:hover:text-cream/50'"
        @click="active = 'a'"
      >
        {{ labelA }}
      </button>
      <button
        class="text-[10px] font-mono transition-colors cursor-pointer"
        :class="active === 'b'
          ? 'text-ink-600 dark:text-ink-400'
          : 'text-body/30 dark:text-cream/30 hover:text-body/50 dark:hover:text-cream/50'"
        @click="active = 'b'"
      >
        {{ labelB }}
      </button>
    </div>
    <slot v-if="active === 'a'" name="a" />
    <slot v-if="active === 'b'" name="b" />
  </div>
</template>

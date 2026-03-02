<script setup lang="ts">
/**
 * RadialProfileChart - Chart.js area chart for Bertaud-style radial density profiles
 *
 * Shows density (people/km²) vs distance from center (km).
 * Supports bidirectional hover sync with the map layer.
 */

import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  type ChartOptions,
  type ChartData,
  type Plugin,
} from 'chart.js'
import { getRingColor } from '~/utils/radialColors'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps<{
  cityId: string
}>()

const { selectedYear } = useSelectedYear()
const { getProfile, getMaxDensity } = useRadialProfiles()
const { highlightedRing, setHighlightedRing } = useRadialHighlight()

// Current profile data
const profile = computed(() => getProfile(props.cityId, selectedYear.value))
const maxDensity = computed(() => getMaxDensity(props.cityId, selectedYear.value))

// Chart data
const chartData = computed<ChartData<'line'>>(() => {
  const densities = profile.value
  if (!densities || densities.length === 0) {
    return { labels: [], datasets: [] }
  }

  const labels = densities.map((_, i) => `${i}`)
  const data = densities.map(d => d ?? 0)

  // Build per-segment colors
  const pointColors = data.map((_, i) => getRingColor(i))

  return {
    labels,
    datasets: [
      {
        data,
        fill: true,
        backgroundColor: 'rgba(139, 37, 0, 0.08)',
        borderColor: pointColors,
        borderWidth: 2,
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
        pointRadius: 0,
        pointHoverRadius: 5,
        tension: 0.3,
        segment: {
          borderColor: (ctx: { p0DataIndex: number }) => getRingColor(ctx.p0DataIndex),
        },
      },
    ],
  }
})

// Chart options
const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  onHover: (_event, elements) => {
    if (elements.length > 0) {
      setHighlightedRing(elements[0]!.index)
    } else {
      setHighlightedRing(null)
    }
  },
  scales: {
    x: {
      title: {
        display: true,
        text: 'km',
        font: { family: 'monospace', size: 10 },
        color: '#8B7355',
      },
      ticks: {
        font: { family: 'monospace', size: 9 },
        color: '#8B7355',
        maxTicksLimit: 10,
      },
      grid: {
        color: 'rgba(139, 115, 85, 0.15)',
      },
    },
    y: {
      title: {
        display: true,
        text: 'density/km²',
        font: { family: 'monospace', size: 10 },
        color: '#8B7355',
      },
      ticks: {
        font: { family: 'monospace', size: 9 },
        color: '#8B7355',
        callback: (value) => {
          const v = Number(value)
          if (v >= 1000) return `${(v / 1000).toFixed(0)}k`
          return `${v}`
        },
      },
      grid: {
        color: 'rgba(139, 115, 85, 0.15)',
      },
      suggestedMax: maxDensity.value * 1.1 || undefined,
    },
  },
  plugins: {
    tooltip: {
      callbacks: {
        title: (items) => {
          if (!items[0]) return ''
          return `Ring ${items[0].dataIndex} (${items[0].dataIndex}-${items[0].dataIndex + 1} km)`
        },
        label: (item) => {
          const density = item.parsed.y ?? 0
          if (density >= 1000) {
            return `${(density / 1000).toFixed(1)}k people/km²`
          }
          return `${density.toFixed(0)} people/km²`
        },
      },
      backgroundColor: 'rgba(92, 74, 61, 0.9)',
      titleFont: { family: 'monospace', size: 11 },
      bodyFont: { family: 'monospace', size: 11 },
    },
    legend: {
      display: false,
    },
  },
}))

// Highlight ring plugin — draws a vertical bar when a ring is highlighted from map hover
const highlightPlugin = computed<Plugin<'line'>>(() => ({
  id: 'radialHighlight',
  afterDraw: (chart) => {
    const ring = highlightedRing.value
    if (ring == null || ring >= (profile.value?.length ?? 0)) return

    const meta = chart.getDatasetMeta(0)
    const point = meta.data[ring]
    if (!point) return

    const { ctx, chartArea } = chart
    const x = point.x

    ctx.save()
    ctx.fillStyle = `${getRingColor(ring)}33`
    const barWidth = chartArea.width / (profile.value?.length ?? 1)
    ctx.fillRect(x - barWidth / 2, chartArea.top, barWidth, chartArea.height)
    ctx.restore()
  },
}))

const plugins = computed(() => [highlightPlugin.value])
</script>

<template>
  <div class="w-full h-[200px]" @mouseleave="setHighlightedRing(null)">
    <div v-if="!profile" class="flex items-center justify-center h-full text-sm text-body/50 dark:text-cream/50">
      No radial profile data
    </div>
    <Line
      v-else
      :data="chartData"
      :options="chartOptions"
      :plugins="plugins"
    />
  </div>
</template>

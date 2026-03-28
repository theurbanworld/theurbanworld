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
import { Legend } from 'chart.js'
import { getDensityColorHex } from '~/utils/densityColors'
import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps<{
  cityId: string
  /** Optional: overlay two cities' radial profiles on the same chart */
  cityIds?: string[]
}>()

const { selectedYear } = useSelectedYear()
const { getProfile, getMaxDensity } = useRadialProfiles()
const { highlightedRing, setHighlightedRing } = useRadialHighlight()
const { getCityName } = useCitiesIndex()

const isComparisonMode = computed(() => !!props.cityIds && props.cityIds.length === 2)

// Current profile data
const profile = computed(() => getProfile(props.cityId, selectedYear.value))
const profileB = computed(() => isComparisonMode.value ? getProfile(props.cityIds![1]!, selectedYear.value) : null)
const maxDensity = computed(() => {
  const maxA = getMaxDensity(props.cityId, selectedYear.value) ?? 0
  if (!isComparisonMode.value) return maxA
  const maxB = getMaxDensity(props.cityIds![1]!, selectedYear.value) ?? 0
  return Math.max(maxA, maxB)
})

// Chart data
const chartData = computed<ChartData<'line'>>(() => {
  const densities = profile.value
  if (!densities || densities.length === 0) {
    return { labels: [], datasets: [] }
  }

  // In comparison mode, use the longer profile's length for labels
  const maxLen = isComparisonMode.value && profileB.value
    ? Math.max(densities.length, profileB.value.length)
    : densities.length
  const labels = Array.from({ length: maxLen }, (_, i) => `${i}`)

  const data = densities.map(d => d ?? 0)

  if (!isComparisonMode.value) {
    // Single city mode — density-intensity sepia gradient
    const maxDen = maxDensity.value || 1
    const pointColors = data.map(d => getDensityColorHex(d, maxDen))
    return {
      labels,
      datasets: [{
        data,
        fill: true,
        backgroundColor: 'rgba(139, 115, 85, 0.08)',
        borderColor: pointColors,
        borderWidth: 2,
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
        pointRadius: 0,
        pointHoverRadius: 5,
        tension: 0.3,
        segment: {
          borderColor: (ctx: { p0DataIndex: number }) => getDensityColorHex(data[ctx.p0DataIndex] ?? 0, maxDen),
        },
      }],
    }
  }

  // Comparison mode — two solid-color datasets
  const datasetA = {
    label: getCityName(props.cityIds![0]!) ?? 'City A',
    data,
    fill: true,
    backgroundColor: CITY_A_COLOR.fill,
    borderColor: CITY_A_COLOR.primary,
    borderWidth: 2,
    pointBackgroundColor: CITY_A_COLOR.primary,
    pointBorderColor: CITY_A_COLOR.primary,
    pointRadius: 0,
    pointHoverRadius: 4,
    tension: 0.3,
  }

  const dataB = profileB.value ? profileB.value.map(d => d ?? 0) : []
  const datasetB = {
    label: getCityName(props.cityIds![1]!) ?? 'City B',
    data: dataB,
    fill: true,
    backgroundColor: CITY_B_COLOR.fill,
    borderColor: CITY_B_COLOR.primary,
    borderWidth: 2,
    pointBackgroundColor: CITY_B_COLOR.primary,
    pointBorderColor: CITY_B_COLOR.primary,
    pointRadius: 0,
    pointHoverRadius: 4,
    tension: 0.3,
  }

  return { labels, datasets: [datasetA, datasetB] }
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
          const prefix = isComparisonMode.value && item.dataset.label ? `${item.dataset.label}: ` : ''
          if (density >= 1000) {
            return `${prefix}${(density / 1000).toFixed(1)}k people/km²`
          }
          return `${prefix}${density.toFixed(0)} people/km²`
        },
      },
      backgroundColor: 'rgba(92, 74, 61, 0.9)',
      titleFont: { family: 'monospace', size: 11 },
      bodyFont: { family: 'monospace', size: 11 },
    },
    legend: {
      display: false,
      labels: {
        boxWidth: 10,
        boxHeight: 10,
        font: { family: 'monospace', size: 10 },
        color: '#8B7355',
        padding: 6,
      },
      position: 'bottom' as const,
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
    const density = profile.value?.[ring] ?? 0
    const maxDen = maxDensity.value || 1
    ctx.fillStyle = `${getDensityColorHex(density, maxDen)}33`
    const barWidth = chartArea.width / (profile.value?.length ?? 1)
    ctx.fillRect(x - barWidth / 2, chartArea.top, barWidth, chartArea.height)
    ctx.restore()
  },
}))

const plugins = computed(() => [highlightPlugin.value])

// Force chart redraw when highlightedRing changes from map hover
const chartRef = ref<{ chart?: ChartJS<'line'> } | null>(null)
watch(highlightedRing, () => {
  chartRef.value?.chart?.update('none')
})
</script>

<template>
  <div class="w-full h-[200px]" @mouseleave="setHighlightedRing(null)">
    <div v-if="!profile" class="flex items-center justify-center h-full text-sm text-body/50 dark:text-cream/50">
      No radial profile data
    </div>
    <Line
      v-else
      ref="chartRef"
      :data="chartData"
      :options="chartOptions"
      :plugins="plugins"
    />
  </div>
</template>

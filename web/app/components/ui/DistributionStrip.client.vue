<script setup lang="ts">
/**
 * DistributionStrip - Compact distribution curve showing a city's rank among all cities
 *
 * Renders a ~25px tall Chart.js filled line chart of all cities sorted by metric value.
 * The current city is highlighted with a vertical marker line.
 * Hovering shows the city name and value at that rank position.
 */

import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LogarithmicScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  type ChartOptions,
  type ChartData,
  type Plugin
} from 'chart.js'
import type { DistributionMetric } from '../../composables/useDistributionData'
import { formatCompactNumber, formatDensity, formatArea } from '../../utils/formatNumber'
import { getMetricDescriptor } from '../../../types/climate'
import { formatClimateValue } from '../../utils/climateFormat'

ChartJS.register(CategoryScale, LinearScale, LogarithmicScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps<{
  cityId: string
  metric: DistributionMetric
}>()

const {
  sortedDistribution,
  cityRank,
  rankLabel,
  getCityAtIndex
} = useDistributionData(
  computed(() => props.cityId),
  computed(() => props.metric)
)

function formatTooltipValue(value: number): string {
  switch (props.metric) {
    case 'population':
      return formatCompactNumber(value)
    case 'density_per_km2':
      return formatDensity(value)
    case 'area_km2':
      return formatArea(value)
    default: {
      // Climate headline metric — format by its catalog unit.
      const descriptor = getMetricDescriptor(props.metric)
      return descriptor ? formatClimateValue(value, descriptor.unit) : String(value)
    }
  }
}

const chartData = computed<ChartData<'line'>>(() => {
  const sorted = sortedDistribution.value
  if (!sorted.length) return { labels: [], datasets: [] }

  const data = sorted.map((entry, i) => ({ x: i, y: entry.value }))

  return {
    datasets: [{
      data,
      fill: true,
      backgroundColor: 'rgba(74, 91, 106, 0.12)',
      borderColor: 'rgba(74, 91, 106, 0.4)',
      borderWidth: 1,
      pointRadius: 0,
      pointHoverRadius: 0,
      tension: 0,
      normalized: true
    }]
  }
})

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'nearest',
    axis: 'x',
    intersect: false
  },
  scales: {
    x: {
      display: false,
      type: 'linear',
      offset: false,
      bounds: 'data'
    },
    y: {
      display: false,
      type: 'logarithmic'
    }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: (items) => {
          if (!items[0]) return ''
          const index = items[0].dataIndex
          const city = getCityAtIndex(index)
          return city?.name ?? ''
        },
        label: (item) => {
          const index = item.dataIndex
          const city = getCityAtIndex(index)
          if (!city) return ''
          return formatTooltipValue(city.value)
        }
      },
      backgroundColor: 'rgba(92, 74, 61, 0.9)',
      titleFont: { family: 'monospace', size: 10 },
      bodyFont: { family: 'monospace', size: 10 },
      padding: 6,
      displayColors: false
    }
  },
  layout: {
    padding: 0
  }
}))

// Plugin to draw a vertical marker at the current city's position
const cityMarkerPlugin = computed<Plugin<'line'>>(() => ({
  id: 'cityMarker',
  afterDraw: (chart) => {
    const rank = cityRank.value
    if (rank < 0) return

    const meta = chart.getDatasetMeta(0)
    if (!meta.data.length) return

    // Find the rendered point closest to our city's rank
    const xScale = chart.scales.x
    if (!xScale) return
    const targetX = xScale.getPixelForValue(rank)

    const { ctx, chartArea } = chart

    // Vertical dashed line
    ctx.save()
    ctx.strokeStyle = 'rgba(180, 140, 60, 0.6)'
    ctx.lineWidth = 1.5
    ctx.setLineDash([3, 2])
    ctx.beginPath()
    ctx.moveTo(targetX, chartArea.top)
    ctx.lineTo(targetX, chartArea.bottom)
    ctx.stroke()

    // Filled dot at the curve intersection
    const yScale = chart.scales.y
    if (yScale) {
      const sorted = sortedDistribution.value
      const entry = sorted[rank]
      if (entry) {
        const targetY = yScale.getPixelForValue(entry.value)
        ctx.fillStyle = 'rgba(180, 140, 60, 0.9)'
        ctx.beginPath()
        ctx.arc(targetX, targetY, 3, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    ctx.restore()
  }
}))

const plugins = computed(() => [cityMarkerPlugin.value])
</script>

<template>
  <div v-if="sortedDistribution.length">
    <div class="flex justify-end">
      <span class="text-[10px] font-mono text-body/50 dark:text-cream/50 leading-none">
        {{ rankLabel }}
      </span>
    </div>
    <div class="h-[40px]">
      <Line
        :data="chartData"
        :options="chartOptions"
        :plugins="plugins"
      />
    </div>
  </div>
</template>

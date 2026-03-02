<script setup lang="ts">
/**
 * EpochSparkline - Compact line chart showing a metric across all epoch years
 *
 * Renders a 40px tall Chart.js line chart with no axes or labels.
 * The currently selected global year is highlighted with a point.
 * Clicking a point changes the global year via useSelectedYear().
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
import { YEAR_EPOCHS } from '../../../types/h3'
import { formatCompactNumber } from '../../utils/formatNumber'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps<{
  cityId: string
  metric: 'population' | 'density_per_km2' | 'area_km2'
}>()

const { selectedYear, setYear } = useSelectedYear()
const { getCityAllEpochs } = useCityPopulations()

const epochs = computed(() => getCityAllEpochs(props.cityId))

function formatTooltipValue(value: number): string {
  switch (props.metric) {
    case 'population':
      return formatCompactNumber(value)
    case 'density_per_km2':
      return `${Math.round(value).toLocaleString()}/km\u00B2`
    case 'area_km2':
      return `${Math.round(value).toLocaleString()} km\u00B2`
  }
}

const chartData = computed<ChartData<'line'>>(() => {
  const epochData = epochs.value
  if (!epochData) return { labels: [], datasets: [] }

  const labels = YEAR_EPOCHS.map(String)
  const data = YEAR_EPOCHS.map(y => epochData[y]?.[props.metric] ?? 0)

  // Highlight selected year point
  const pointRadius = YEAR_EPOCHS.map(y => y === selectedYear.value ? 4 : 0)
  const pointHoverRadius = YEAR_EPOCHS.map(y => y === selectedYear.value ? 5 : 3)

  return {
    labels,
    datasets: [{
      data,
      fill: true,
      backgroundColor: 'rgba(181, 201, 175, 0.2)',
      borderColor: '#4A6741',
      borderWidth: 1.5,
      pointBackgroundColor: '#4A6741',
      pointBorderColor: '#4A6741',
      pointRadius,
      pointHoverRadius,
      tension: 0.3,
    }],
  }
})

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  onClick: (_event, elements) => {
    if (elements.length > 0) {
      const index = elements[0]!.index
      const year = YEAR_EPOCHS[index]
      if (year !== undefined) setYear(year)
    }
  },
  onHover: (event, elements) => {
    const canvas = event.native?.target as HTMLCanvasElement | undefined
    if (canvas) {
      canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default'
    }
  },
  scales: {
    x: { display: false },
    y: { display: false, beginAtZero: true },
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: (items) => {
          if (!items[0]) return ''
          return items[0].label ?? ''
        },
        label: (item) => formatTooltipValue(item.parsed.y ?? 0),
      },
      backgroundColor: 'rgba(92, 74, 61, 0.9)',
      titleFont: { family: 'monospace', size: 10 },
      bodyFont: { family: 'monospace', size: 10 },
      padding: 6,
      displayColors: false,
    },
  },
  layout: {
    padding: 0,
  },
}))

// Vertical indicator line plugin for selected year
const selectedYearPlugin = computed<Plugin<'line'>>(() => ({
  id: 'selectedYearIndicator',
  afterDraw: (chart) => {
    const yearIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (yearIndex < 0) return

    const meta = chart.getDatasetMeta(0)
    const point = meta.data[yearIndex]
    if (!point) return

    const { ctx, chartArea } = chart
    ctx.save()
    ctx.strokeStyle = 'rgba(74, 103, 65, 0.3)'
    ctx.lineWidth = 1
    ctx.setLineDash([2, 2])
    ctx.beginPath()
    ctx.moveTo(point.x, chartArea.top)
    ctx.lineTo(point.x, chartArea.bottom)
    ctx.stroke()
    ctx.restore()
  },
}))

const plugins = computed(() => [selectedYearPlugin.value])
</script>

<template>
  <div v-if="epochs" class="h-[40px]">
    <Line :data="chartData" :options="chartOptions" :plugins="plugins" />
  </div>
</template>

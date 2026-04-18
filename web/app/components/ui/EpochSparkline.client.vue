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
  type Plugin
} from 'chart.js'
import { YEAR_EPOCHS } from '../../../types/h3'
import { formatCompactNumber } from '../../utils/formatNumber'
import { CITY_A_COLOR, CITY_B_COLOR } from '../../utils/comparisonColors'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps<{
  cityId: string
  metric: 'population' | 'density_per_km2' | 'area_km2'
  /** Optional: overlay two cities' data on the same chart */
  cityIds?: string[]
  /** Year the city first became an urban center (enables dashed pre-birth segments) */
  birthYear?: number
  /** Year the city fell below urban center threshold (enables dashed post-death segments) */
  deathYear?: number
}>()

const { selectedYear, setYear } = useSelectedYear()
const { getCityAllEpochs } = useCityPopulations()
const { getCityName } = useCitiesIndex()

const isComparisonMode = computed(() => !!props.cityIds && props.cityIds.length === 2)
const epochs = computed(() => getCityAllEpochs(props.cityId))
const epochsB = computed(() => isComparisonMode.value ? getCityAllEpochs(props.cityIds![1]!) : null)

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

  // Build segment styling for pre-birth / post-death dashed lines
  const birthIdx = props.birthYear ? YEAR_EPOCHS.indexOf(props.birthYear as typeof YEAR_EPOCHS[number]) : -1
  const deathIdx = props.deathYear ? YEAR_EPOCHS.indexOf(props.deathYear as typeof YEAR_EPOCHS[number]) : -1

  const segmentStyle = (birthIdx >= 0 || deathIdx >= 0)
    ? {
        segment: {
          borderColor: (ctx: { p0DataIndex: number, p1DataIndex: number }) => {
            if (birthIdx >= 0 && ctx.p1DataIndex < birthIdx) return 'rgba(180, 150, 100, 0.5)'
            if (deathIdx >= 0 && ctx.p0DataIndex >= deathIdx) return 'rgba(140, 140, 140, 0.5)'
            return undefined
          },
          borderDash: (ctx: { p0DataIndex: number, p1DataIndex: number }) => {
            if (birthIdx >= 0 && ctx.p1DataIndex < birthIdx) return [4, 3]
            if (deathIdx >= 0 && ctx.p0DataIndex >= deathIdx) return [4, 3]
            return undefined
          }
        }
      }
    : {}

  const datasetA = {
    label: isComparisonMode.value ? (getCityName(props.cityIds![0]!) ?? 'City A') : undefined,
    data,
    fill: true,
    backgroundColor: isComparisonMode.value ? CITY_A_COLOR.fill : 'rgba(74, 91, 106, 0.15)',
    borderColor: isComparisonMode.value ? CITY_A_COLOR.primary : '#4A5B6A',
    borderWidth: 1.5,
    pointBackgroundColor: isComparisonMode.value ? CITY_A_COLOR.primary : '#4A5B6A',
    pointBorderColor: isComparisonMode.value ? CITY_A_COLOR.primary : '#4A5B6A',
    pointRadius,
    pointHoverRadius,
    tension: 0.3,
    ...segmentStyle
  }

  if (!isComparisonMode.value || !epochsB.value) {
    return { labels, datasets: [datasetA] }
  }

  // Comparison mode — add city B dataset
  const dataB = YEAR_EPOCHS.map(y => epochsB.value![y]?.[props.metric] ?? 0)
  const pointRadiusB = YEAR_EPOCHS.map(y => y === selectedYear.value ? 4 : 0)
  const pointHoverRadiusB = YEAR_EPOCHS.map(y => y === selectedYear.value ? 5 : 3)

  const datasetB = {
    label: getCityName(props.cityIds![1]!) ?? 'City B',
    data: dataB,
    fill: true,
    backgroundColor: CITY_B_COLOR.fill,
    borderColor: CITY_B_COLOR.primary,
    borderWidth: 1.5,
    pointBackgroundColor: CITY_B_COLOR.primary,
    pointBorderColor: CITY_B_COLOR.primary,
    pointRadius: pointRadiusB,
    pointHoverRadius: pointHoverRadiusB,
    tension: 0.3
  }

  return { labels, datasets: [datasetA, datasetB] }
})

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false
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
    y: { display: false, beginAtZero: true }
  },
  plugins: {
    legend: {
      display: false,
      labels: {
        boxWidth: 8,
        boxHeight: 8,
        font: { family: 'monospace', size: 9 },
        color: '#8B7355',
        padding: 4
      },
      position: 'bottom' as const
    },
    tooltip: {
      callbacks: {
        title: (items) => {
          if (!items[0]) return ''
          return items[0].label ?? ''
        },
        label: item => formatTooltipValue(item.parsed.y ?? 0)
      },
      backgroundColor: 'rgba(92, 74, 61, 0.9)',
      titleFont: { family: 'monospace', size: 10 },
      bodyFont: { family: 'monospace', size: 10 },
      padding: 6,
      displayColors: isComparisonMode.value
    }
  },
  layout: {
    padding: 0
  }
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
    ctx.strokeStyle = 'rgba(74, 91, 106, 0.3)'
    ctx.lineWidth = 1
    ctx.setLineDash([2, 2])
    ctx.beginPath()
    ctx.moveTo(point.x, chartArea.top)
    ctx.lineTo(point.x, chartArea.bottom)
    ctx.stroke()
    ctx.restore()
  }
}))

// Vertical marker lines at birth/death year transitions
const lifecycleMarkerPlugin = computed<Plugin<'line'>>(() => ({
  id: 'lifecycleMarker',
  afterDraw: (chart) => {
    const drawMarker = (yearIndex: number, color: string) => {
      if (yearIndex < 0) return
      const meta = chart.getDatasetMeta(0)
      const point = meta.data[yearIndex]
      if (!point) return

      const { ctx, chartArea } = chart
      ctx.save()
      ctx.strokeStyle = color
      ctx.lineWidth = 1
      ctx.setLineDash([1, 2])
      ctx.beginPath()
      ctx.moveTo(point.x, chartArea.top)
      ctx.lineTo(point.x, chartArea.bottom)
      ctx.stroke()
      ctx.restore()
    }

    if (props.birthYear) {
      const idx = YEAR_EPOCHS.indexOf(props.birthYear as typeof YEAR_EPOCHS[number])
      drawMarker(idx, 'rgba(180, 130, 50, 0.6)')
    }
    if (props.deathYear) {
      const idx = YEAR_EPOCHS.indexOf(props.deathYear as typeof YEAR_EPOCHS[number])
      drawMarker(idx, 'rgba(140, 140, 140, 0.6)')
    }
  }
}))

const plugins = computed(() => [selectedYearPlugin.value, lifecycleMarkerPlugin.value])
</script>

<template>
  <div
    v-if="epochs"
    :class="isComparisonMode ? 'h-[65px]' : 'h-[40px]'"
  >
    <Line
      :data="chartData"
      :options="chartOptions"
      :plugins="plugins"
    />
  </div>
</template>

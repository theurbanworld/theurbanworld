<script setup lang="ts">
/**
 * NativeAxisSparkline — a compact Chart.js line over a metric's OWN year keys.
 *
 * Unlike EpochSparkline, this renders against the metric's native spine (the
 * variable {year, value} points passed in), decoupled from the global epoch
 * slider (no useSelectedYear, no point-click year mutation). This avoids
 * implying data points at population epochs where a climate series has none.
 *
 * Single-point or empty series render a flat "—" state, never a crash.
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
  type ChartData
} from 'chart.js'
import type { SeriesPoint } from '../../utils/climateFormat'
import { hasSeries, nativeSparklineData, formatClimateValue } from '../../utils/climateFormat'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps<{
  points: SeriesPoint[]
  unit?: string | null
  label?: string
}>()

const renderable = computed(() => hasSeries(props.points))

const chartData = computed<ChartData<'line'>>(() => {
  const { labels, values } = nativeSparklineData(props.points ?? [])
  return {
    labels,
    datasets: [
      {
        label: props.label ?? '',
        data: values,
        fill: true,
        backgroundColor: 'rgba(74, 91, 106, 0.15)',
        borderColor: '#4A5B6A',
        borderWidth: 1.5,
        pointBackgroundColor: '#4A5B6A',
        pointBorderColor: '#4A5B6A',
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.3
      }
    ]
  }
})

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  scales: {
    x: { display: false },
    y: { display: false, beginAtZero: false }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: items => items[0]?.label ?? '',
        label: item => formatClimateValue(item.parsed.y ?? 0, props.unit ?? null)
      },
      backgroundColor: 'rgba(92, 74, 61, 0.9)',
      titleFont: { family: 'monospace', size: 10 },
      bodyFont: { family: 'monospace', size: 10 },
      padding: 6,
      displayColors: false
    }
  },
  layout: { padding: 0 }
}))
</script>

<template>
  <div class="h-[40px]">
    <Line
      v-if="renderable"
      data-testid="native-axis-sparkline"
      :data="chartData"
      :options="chartOptions"
    />
    <div
      v-else
      data-testid="native-axis-sparkline-empty"
      class="h-full flex items-center text-xs font-mono text-body/30 dark:text-cream/30"
    >
      —
    </div>
  </div>
</template>

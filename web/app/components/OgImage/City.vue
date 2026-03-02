<script setup lang="ts">
/**
 * OG image template for city pages.
 *
 * Renders city outline shape, name, country, and key stats
 * for social media previews. Uses Satori renderer (edge-compatible).
 */

const props = withDefaults(defineProps<{
  cityName?: string
  countryName?: string
  population?: string
  density?: string
  area?: string
  outlineUrl?: string
}>(), {
  cityName: 'City',
  countryName: '',
  population: '',
  density: '',
  area: '',
  outlineUrl: ''
})

// Fetch and process outline data
const svgPath = ref('')
const viewBox = ref('0 0 400 280')

async function loadOutline() {
  if (!props.outlineUrl) return

  try {
    const data = await $fetch<{ coordinates: number[][][] }>(props.outlineUrl)
    if (!data?.coordinates?.length) return

    // Compute bounding box across all rings
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const ring of data.coordinates) {
      for (const [lon, lat] of ring) {
        if (lon < minX) minX = lon
        if (lon > maxX) maxX = lon
        if (lat < minY) minY = lat
        if (lat > maxY) maxY = lat
      }
    }

    // SVG canvas for the outline area
    const svgW = 400
    const svgH = 280
    const padding = 20

    const bboxW = maxX - minX || 1
    const bboxH = maxY - minY || 1

    // Fit within padded area, preserving aspect ratio
    const scale = Math.min(
      (svgW - padding * 2) / bboxW,
      (svgH - padding * 2) / bboxH
    )

    const projW = bboxW * scale
    const projH = bboxH * scale
    const offsetX = (svgW - projW) / 2
    const offsetY = (svgH - projH) / 2

    // Project coordinates to SVG space (flip Y since lat increases upward)
    function project(lon: number, lat: number): [number, number] {
      const x = (lon - minX) * scale + offsetX
      const y = (maxY - lat) * scale + offsetY
      return [Math.round(x * 10) / 10, Math.round(y * 10) / 10]
    }

    // Build SVG path string for all rings
    const paths: string[] = []
    for (const ring of data.coordinates) {
      const points = ring.map(([lon, lat]) => project(lon, lat))
      if (points.length < 3) continue
      const d = `M${points[0][0]},${points[0][1]}` +
        points.slice(1).map(([x, y]) => `L${x},${y}`).join('') +
        'Z'
      paths.push(d)
    }

    svgPath.value = paths.join(' ')
    viewBox.value = `0 0 ${svgW} ${svgH}`
  } catch {
    // Outline unavailable — render without it
  }
}

await loadOutline()
</script>

<template>
  <div
    :style="{
      width: '1200px',
      height: '630px',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#FAFAF4',
      fontFamily: 'Inter, sans-serif',
      position: 'relative',
      overflow: 'hidden'
    }"
  >
    <!-- City outline -->
    <div
      :style="{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flex: '1',
        padding: '40px 80px 0'
      }"
    >
      <svg
        v-if="svgPath"
        :viewBox="viewBox"
        :style="{
          width: '400px',
          height: '280px'
        }"
      >
        <path
          :d="svgPath"
          fill="rgba(106, 143, 94, 0.25)"
          stroke="#3A5233"
          stroke-width="1.5"
        />
      </svg>
      <!-- Fallback when no outline available -->
      <div
        v-else
        :style="{
          width: '400px',
          height: '280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }"
      >
        <div
          :style="{
            width: '120px',
            height: '120px',
            borderRadius: '50%',
            backgroundColor: 'rgba(106, 143, 94, 0.15)',
            border: '2px solid rgba(58, 82, 51, 0.3)'
          }"
        />
      </div>
    </div>

    <!-- City info -->
    <div
      :style="{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '0 80px 20px',
        gap: '8px'
      }"
    >
      <!-- City name -->
      <div
        :style="{
          fontFamily: 'Crimson Pro, serif',
          fontSize: '52px',
          fontWeight: 600,
          color: '#3A5233',
          lineHeight: '1.1'
        }"
      >
        {{ cityName }}
      </div>

      <!-- Country -->
      <div
        v-if="countryName"
        :style="{
          fontSize: '22px',
          color: '#4A4238',
          lineHeight: '1.2'
        }"
      >
        {{ countryName }}
      </div>

      <!-- Stats row -->
      <div
        v-if="population || density || area"
        :style="{
          display: 'flex',
          alignItems: 'center',
          gap: '32px',
          marginTop: '8px'
        }"
      >
        <div v-if="population" :style="{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }">
          <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '26px', color: '#5C4A3D', fontWeight: 600 }">
            {{ population }}
          </div>
          <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
            Population
          </div>
        </div>

        <div
          v-if="population && density"
          :style="{ width: '1px', height: '32px', backgroundColor: 'rgba(74, 66, 56, 0.2)' }"
        />

        <div v-if="density" :style="{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }">
          <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '26px', color: '#5C4A3D', fontWeight: 600 }">
            {{ density }}
          </div>
          <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
            Density
          </div>
        </div>

        <div
          v-if="density && area"
          :style="{ width: '1px', height: '32px', backgroundColor: 'rgba(74, 66, 56, 0.2)' }"
        />

        <div v-if="area" :style="{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }">
          <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '26px', color: '#5C4A3D', fontWeight: 600 }">
            {{ area }}
          </div>
          <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
            Area
          </div>
        </div>
      </div>
    </div>

    <!-- Branding footer -->
    <div
      :style="{
        display: 'flex',
        justifyContent: 'center',
        padding: '16px 0 24px',
        borderTop: '1px solid rgba(58, 82, 51, 0.15)'
      }"
    >
      <div
        :style="{
          fontFamily: 'Crimson Pro, serif',
          fontSize: '18px',
          fontWeight: 600,
          color: '#3A5233',
          letterSpacing: '0.05em'
        }"
      >
        The Urban World
      </div>
    </div>
  </div>
</template>

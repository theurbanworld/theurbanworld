<script setup lang="ts">
/**
 * OG image template for comparison pages.
 *
 * City A (name + stats) is left-aligned, City B is right-aligned, and the two
 * city outlines are overlaid in the center in distinct colors so the relative
 * shape/scale reads at a glance. Uses Satori renderer (edge-compatible).
 */

const props = withDefaults(defineProps<{
  cityAName?: string
  cityACountry?: string
  cityAPopulation?: string
  cityADensity?: string
  cityAArea?: string
  cityAOutlineUrl?: string
  cityBName?: string
  cityBCountry?: string
  cityBPopulation?: string
  cityBDensity?: string
  cityBArea?: string
  cityBOutlineUrl?: string
}>(), {
  cityAName: 'City A',
  cityACountry: '',
  cityAPopulation: '',
  cityADensity: '',
  cityAArea: '',
  cityAOutlineUrl: '',
  cityBName: 'City B',
  cityBCountry: '',
  cityBPopulation: '',
  cityBDensity: '',
  cityBArea: '',
  cityBOutlineUrl: ''
})

// Distinct colors for the two cities (ink slate vs. brass/rust)
const COLOR_A = '#3A4856'
const COLOR_B = '#B5651D'

// Shared canvas so both outlines overlay centered at the same scale reference
const CANVAS_W = 480
const CANVAS_H = 460

// Project an outline GeoJSON ring set into an SVG path on the shared canvas.
async function loadOutline(url: string): Promise<string> {
  if (!url) return ''

  try {
    const data = await $fetch<{ coordinates: number[][][] }>(url)
    if (!data?.coordinates?.length) return ''

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const ring of data.coordinates) {
      for (const coord of ring) {
        const lon = coord[0]!
        const lat = coord[1]!
        if (lon < minX) minX = lon
        if (lon > maxX) maxX = lon
        if (lat < minY) minY = lat
        if (lat > maxY) maxY = lat
      }
    }

    const padding = 24
    const bboxW = maxX - minX || 1
    const bboxH = maxY - minY || 1

    const scale = Math.min(
      (CANVAS_W - padding * 2) / bboxW,
      (CANVAS_H - padding * 2) / bboxH
    )

    const projW = bboxW * scale
    const projH = bboxH * scale
    const offsetX = (CANVAS_W - projW) / 2
    const offsetY = (CANVAS_H - projH) / 2

    function project(lon: number, lat: number): [number, number] {
      const x = (lon - minX) * scale + offsetX
      const y = (maxY - lat) * scale + offsetY
      return [Math.round(x * 10) / 10, Math.round(y * 10) / 10]
    }

    const paths: string[] = []
    for (const ring of data.coordinates) {
      const points = ring.map(coord => project(coord[0]!, coord[1]!))
      if (points.length < 3) continue
      const first = points[0]!
      const d = `M${first[0]},${first[1]}`
        + points.slice(1).map(([x, y]) => `L${x},${y}`).join('')
        + 'Z'
      paths.push(d)
    }

    return paths.join(' ')
  } catch {
    return ''
  }
}

const svgPathA = ref('')
const svgPathB = ref('')

svgPathA.value = await loadOutline(props.cityAOutlineUrl)
svgPathB.value = await loadOutline(props.cityBOutlineUrl)

// Small-caps emulation for the footer wordmark (Satori doesn't render
// `font-variant: small-caps`), matching the web app header (AppLogo.vue).
const WORDMARK = [
  { lead: 'T', rest: 'HE' },
  { lead: 'U', rest: 'RBAN' },
  { lead: 'W', rest: 'ORLD' }
]
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
      overflow: 'hidden',
      padding: '28px 64px 104px'
    }"
  >
    <!-- Content row: city A (left), overlaid maps (center), city B (right) -->
    <div
      :style="{
        display: 'flex',
        flex: '1',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px'
      }"
    >
      <!-- City A — left aligned -->
      <div
        :style="{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'flex-start',
          width: '320px',
          flexShrink: 0,
          gap: '6px'
        }"
      >
        <div
          :style="{
            fontFamily: 'Crimson Pro, serif',
            fontSize: '48px',
            fontWeight: 600,
            color: COLOR_A,
            lineHeight: '1.05'
          }"
        >
          {{ cityAName }}
        </div>
        <div
          v-if="cityACountry"
          :style="{ fontSize: '22px', color: '#4A4238', lineHeight: '1.2' }"
        >
          {{ cityACountry }}
        </div>

        <div
          v-if="cityAPopulation || cityADensity || cityAArea"
          :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '14px', marginTop: '22px' }"
        >
          <div
            v-if="cityAPopulation"
            :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }"
          >
            <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
              Population
            </div>
            <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '28px', fontWeight: 600, color: '#5C4A3D', lineHeight: '1.1' }">
              {{ cityAPopulation }}
            </div>
          </div>
          <div
            v-if="cityADensity"
            :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }"
          >
            <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
              Density
            </div>
            <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '28px', fontWeight: 600, color: '#5C4A3D', lineHeight: '1.1' }">
              {{ cityADensity }}
            </div>
          </div>
          <div
            v-if="cityAArea"
            :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }"
          >
            <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
              Area
            </div>
            <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '28px', fontWeight: 600, color: '#5C4A3D', lineHeight: '1.1' }">
              {{ cityAArea }}
            </div>
          </div>
        </div>
      </div>

      <!-- Center: two outlines overlaid -->
      <div
        :style="{
          display: 'flex',
          flex: '1',
          alignItems: 'center',
          justifyContent: 'center'
        }"
      >
        <div
          :style="{
            display: 'flex',
            position: 'relative',
            width: `${CANVAS_W}px`,
            height: `${CANVAS_H}px`
          }"
        >
          <svg
            v-if="svgPathA"
            :viewBox="`0 0 ${CANVAS_W} ${CANVAS_H}`"
            :style="{ position: 'absolute', top: '0px', left: '0px', width: `${CANVAS_W}px`, height: `${CANVAS_H}px` }"
          >
            <path
              :d="svgPathA"
              fill="rgba(58, 72, 86, 0.30)"
              :stroke="COLOR_A"
              stroke-width="2"
            />
          </svg>
          <svg
            v-if="svgPathB"
            :viewBox="`0 0 ${CANVAS_W} ${CANVAS_H}`"
            :style="{ position: 'absolute', top: '0px', left: '0px', width: `${CANVAS_W}px`, height: `${CANVAS_H}px` }"
          >
            <path
              :d="svgPathB"
              fill="rgba(181, 101, 29, 0.30)"
              :stroke="COLOR_B"
              stroke-width="2"
            />
          </svg>
        </div>
      </div>

      <!-- City B — right aligned -->
      <div
        :style="{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'flex-end',
          width: '320px',
          flexShrink: 0,
          gap: '6px'
        }"
      >
        <div
          :style="{
            fontFamily: 'Crimson Pro, serif',
            fontSize: '48px',
            fontWeight: 600,
            color: COLOR_B,
            lineHeight: '1.05',
            textAlign: 'right'
          }"
        >
          {{ cityBName }}
        </div>
        <div
          v-if="cityBCountry"
          :style="{ fontSize: '22px', color: '#4A4238', lineHeight: '1.2', textAlign: 'right' }"
        >
          {{ cityBCountry }}
        </div>

        <div
          v-if="cityBPopulation || cityBDensity || cityBArea"
          :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '14px', marginTop: '22px' }"
        >
          <div
            v-if="cityBPopulation"
            :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }"
          >
            <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
              Population
            </div>
            <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '28px', fontWeight: 600, color: '#5C4A3D', lineHeight: '1.1' }">
              {{ cityBPopulation }}
            </div>
          </div>
          <div
            v-if="cityBDensity"
            :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }"
          >
            <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
              Density
            </div>
            <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '28px', fontWeight: 600, color: '#5C4A3D', lineHeight: '1.1' }">
              {{ cityBDensity }}
            </div>
          </div>
          <div
            v-if="cityBArea"
            :style="{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }"
          >
            <div :style="{ fontSize: '12px', color: 'rgba(74, 66, 56, 0.6)', textTransform: 'uppercase', letterSpacing: '0.08em' }">
              Area
            </div>
            <div :style="{ fontFamily: 'Crimson Pro, serif', fontSize: '28px', fontWeight: 600, color: '#5C4A3D', lineHeight: '1.1' }">
              {{ cityBArea }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Branding footer: icon + wordmark, centered at bottom -->
    <div
      :style="{
        position: 'absolute',
        bottom: '52px',
        left: '0px',
        width: '1200px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '14px'
      }"
    >
      <svg
        viewBox="8 104 440 336"
        :style="{ width: '36px', height: '36px' }"
      >
        <g transform="matrix(0.435873 0 0 0.435547 6.10352e-05 0)">
          <path
            fill="#3A4856"
            d="M466.766 644.743C476.322 645.019 488.633 646.414 498.247 647.678C556.481 655.331 604.311 676.412 645.813 718.146C728.364 801.158 717.502 896.677 716.624 1004.55C713.451 1005.14 699.23 1004.92 695.029 1004.91L649.997 1004.88L466.244 1004.85L466.766 644.743Z"
          />
          <path
            fill="#3A4856"
            d="M324.445 481.334L442.509 481.011L441.423 1004.66L425.996 1004.76C386.986 1005.05 347.975 1005.06 308.965 1004.78L309.096 481.493L324.445 481.334Z"
          />
          <path
            fill="#3A4856"
            d="M724.988 481.521L844.342 481.53L844.322 832.715L844.287 949.267L844.242 985.604C844.238 990.102 844.537 999.352 844.167 1003.41L843.272 1004.1C829.365 1005.33 813.371 1005.21 799.373 1005.19C779.511 1005.17 759.651 1004.96 739.793 1004.58L739.631 919.648C739.44 899.02 738.906 878.16 737.31 857.578C735.738 837.31 726.227 816.162 725.466 796.101C725.026 784.494 725.067 771.55 724.948 759.879L724.716 675.113C724.371 610.583 724.461 546.051 724.988 481.521Z"
          />
          <path
            fill="#3A4856"
            d="M798.524 293.25C814.298 293.231 830.071 293.336 845.843 293.565C845.242 347.531 845.898 402.57 845.813 456.655L700.954 456.746C700.085 554.041 699.942 651.34 700.527 748.637C696.506 744.566 690.794 736.033 687.197 730.993C682.737 724.635 677.978 718.493 672.937 712.586C650.98 686.227 619.634 666.203 590.065 649.49L589.894 549.415C589.593 484.917 586.445 431.357 625.866 376.098C662.688 324.482 714.067 299.936 776.472 294.029C783.68 293.346 791.22 293.388 798.524 293.25Z"
          />
          <path
            fill="#3A4856"
            d="M206.036 244.529L351.865 244.69C382.749 244.808 413.633 244.76 444.516 244.547L444.337 456.136L444.083 456.564C442.443 457.445 229.443 456.722 206.15 456.723L206.095 330.946C206.044 302.266 205.733 273.18 206.036 244.529Z"
          />
          <path
            fill="#3A4856"
            d="M22.7661 696.491L183.064 696.466L182.236 1004.21C132.617 1007.53 73.48 1005.1 22.6919 1004.55L22.7661 696.491Z"
          />
          <path
            fill="#3A4856"
            d="M881.945 696.785C929.401 696.136 977.623 696.499 1025.13 696.441L1024.96 1004.81L1010.5 1004.82L868.138 1004.86L868.26 696.944L881.945 696.785Z"
          />
          <path
            fill="#3A4856"
            d="M206.987 481.107L283.765 481.156C285.117 655.643 285.141 830.137 283.837 1004.62C279.162 1005.16 263.664 1004.79 258.37 1004.79L206.71 1004.75L206.987 481.107Z"
          />
          <path
            fill="#3A4856"
            d="M179.066 482.123C180.075 482.141 179.573 482.063 180.547 482.694C182.902 490.556 183.465 530.768 183.561 541.072C184 584.988 183.697 628.909 182.652 672.815L28.2562 672.341C22.169 671.231 22.4531 665.726 23.0515 660.805C26.5171 632.305 33.7566 606.108 47.5477 580.794C74.9456 530.504 124.642 497.587 179.066 482.123Z"
          />
          <path
            fill="#3A4856"
            d="M868.107 482.397C902.532 488.874 934.419 504.974 960.072 528.832C1000.77 566.571 1022.83 617.424 1024.88 672.706C1006.19 673.035 986.789 672.688 968.031 672.647L868.132 672.534L868.107 482.397Z"
          />
        </g>
      </svg>
      <div
        :style="{
          display: 'flex',
          alignItems: 'baseline',
          gap: '11px',
          fontFamily: 'Crimson Pro, serif',
          fontWeight: 600,
          color: '#3A4856',
          letterSpacing: '0.01em'
        }"
      >
        <div
          v-for="w in WORDMARK"
          :key="w.lead"
          :style="{ display: 'flex', alignItems: 'baseline' }"
        >
          <div :style="{ fontSize: '46px', lineHeight: '1' }">
            {{ w.lead }}
          </div>
          <div :style="{ fontSize: '34px', lineHeight: '1' }">
            {{ w.rest }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

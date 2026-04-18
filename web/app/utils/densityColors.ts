/**
 * Density-intensity color scale for radial profiles
 *
 * Maps density values to a spectral gradient where higher density = hotter.
 * Low density: pale/cool → high density: warm/purple.
 * Used by both the map layer (deck.gl RGBA) and chart (hex strings).
 */

import type { RGBAColor } from './colorScale'

/**
 * 8-step spectral gradient: sparse → dense
 * Inspired by meteorology/heatmap palettes.
 */
const SPECTRAL: readonly RGBAColor[] = [
  [199, 213, 192, 255], // #C7D5C0 - Pale sage (very low)
  [161, 194, 152, 255], // #A1C298 - Soft green (low)
  [120, 185, 145, 255], // #78B991 - Teal green
  [218, 165, 32, 255], // #DAA520 - Goldenrod
  [210, 120, 26, 255], // #D2781A - Orange
  [184, 69, 10, 255], // #B8450A - Burnt orange
  [139, 37, 0, 255], // #8B2500 - Deep rust
  [106, 90, 205, 255] // #6A5ACD - Slate purple (peak)
]

/**
 * Linearly interpolate between two RGBA colors
 */
function lerpRGBA(a: RGBAColor, b: RGBAColor, t: number): RGBAColor {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
    Math.round(a[3] + (b[3] - a[3]) * t)
  ]
}

function rgbaToHex(c: RGBAColor): string {
  return `#${c[0].toString(16).padStart(2, '0')}${c[1].toString(16).padStart(2, '0')}${c[2].toString(16).padStart(2, '0')}`
}

/**
 * Map a density value to an RGBA color on the spectral gradient.
 * t = density / maxDensity, clamped to [0, 1], interpolated across stops.
 */
export function getDensityColorRGBA(
  density: number | null,
  maxDensity: number,
  _isDarkMode: boolean = false,
  alpha: number = 220
): RGBAColor {
  if (density == null || density <= 0 || maxDensity <= 0) {
    const c = SPECTRAL[0]!
    return [c[0], c[1], c[2], alpha]
  }

  const t = Math.min(density / maxDensity, 1)
  const scaledIndex = t * (SPECTRAL.length - 1)
  const lower = Math.floor(scaledIndex)
  const upper = Math.min(lower + 1, SPECTRAL.length - 1)
  const frac = scaledIndex - lower

  const color = lerpRGBA(SPECTRAL[lower]!, SPECTRAL[upper]!, frac)
  return [color[0], color[1], color[2], alpha]
}

/**
 * Map a density value to a hex color string (for Chart.js).
 */
export function getDensityColorHex(
  density: number | null,
  maxDensity: number
): string {
  const rgba = getDensityColorRGBA(density, maxDensity, false, 255)
  return rgbaToHex(rgba)
}

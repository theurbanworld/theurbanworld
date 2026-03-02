/**
 * Ring color gradient for radial density profiles
 *
 * 10-color gradient for ring distance, used by both chart and map layer.
 * Center (ring 0) is warm/dark, edge is cool/light.
 */

import type { RGBAColor } from './colorScale'

/**
 * 10-step ring distance color gradient
 * Center (densest) → Edge (sparse)
 */
export const RING_COLORS: string[] = [
  '#8B2500', // 0km — deep rust
  '#B8450A', // 1km
  '#D4781A', // 2km
  '#DAA520', // 3km — goldenrod
  '#8FBC3B', // 4km
  '#4A9A5B', // 5km — forest
  '#3A7CA5', // 6km
  '#4169E1', // 7km — royal blue
  '#6A5ACD', // 8km — slate purple
  '#9B8EC0', // 9km+ — light purple
]

/** Pale neutral for outer rings beyond the gradient */
const OUTER_COLOR = '#C4BDB0'

/**
 * Get the hex color for a ring index
 */
export function getRingColor(ringIndex: number): string {
  if (ringIndex < 0) return RING_COLORS[0]!
  if (ringIndex < RING_COLORS.length) return RING_COLORS[ringIndex]!

  // Interpolate toward pale neutral for outer rings
  const lastColor = RING_COLORS[RING_COLORS.length - 1]!
  const t = Math.min((ringIndex - RING_COLORS.length + 1) / 10, 1)
  return lerpHexColor(lastColor, OUTER_COLOR, t)
}

/**
 * Get the RGBA color for a ring index (for deck.gl)
 */
export function getRingColorRGBA(ringIndex: number, alpha: number = 220): RGBAColor {
  const hex = getRingColor(ringIndex)
  return hexToRGBALocal(hex, alpha)
}

/**
 * Linear interpolation between two hex colors
 */
function lerpHexColor(a: string, b: string, t: number): string {
  const [r1, g1, b1] = parseHex(a)
  const [r2, g2, b2] = parseHex(b)
  const r = Math.round(r1 + (r2 - r1) * t)
  const g = Math.round(g1 + (g2 - g1) * t)
  const bl = Math.round(b1 + (b2 - b1) * t)
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${bl.toString(16).padStart(2, '0')}`
}

function parseHex(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [
    parseInt(h.substring(0, 2), 16),
    parseInt(h.substring(2, 4), 16),
    parseInt(h.substring(4, 6), 16),
  ]
}

function hexToRGBALocal(hex: string, alpha: number): RGBAColor {
  const [r, g, b] = parseHex(hex)
  return [r, g, b, alpha]
}

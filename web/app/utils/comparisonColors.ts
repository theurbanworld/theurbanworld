/**
 * City A/B visual identity colors for comparison mode
 *
 * Used across maps (city labels), metric table (column headers),
 * and overlay charts (datasets and legends).
 */

export const CITY_A_COLOR = {
  /** Primary color for city A — forest green matching existing theme */
  primary: '#2d5016',
  /** Light variant for backgrounds and fills */
  light: 'rgba(45, 80, 22, 0.15)',
  /** Chart fill */
  fill: 'rgba(45, 80, 22, 0.08)',
  /** Tailwind class for text */
  textClass: 'text-forest-700 dark:text-forest-400',
  /** Tailwind class for background dot */
  dotClass: 'bg-forest-700 dark:bg-forest-400'
} as const

export const CITY_B_COLOR = {
  /** Primary color for city B — warm amber/terracotta */
  primary: '#b45309',
  /** Light variant for backgrounds and fills */
  light: 'rgba(180, 83, 9, 0.15)',
  /** Chart fill */
  fill: 'rgba(180, 83, 9, 0.08)',
  /** Tailwind class for text */
  textClass: 'text-amber-700 dark:text-amber-400',
  /** Tailwind class for background dot */
  dotClass: 'bg-amber-700 dark:bg-amber-400'
} as const

# Cartography

A sepia-toned "old atlas" aesthetic for The Urban World.

## Basemap Colors

The basemap is your canvas — it should feel muted and recede so the density data pops.

| Element | Color | Hex | Notes |
| --- | --- | --- | --- |
| Land (default) | Parchment | `#F5F1E6` | Warm off-white, like aged paper |
| Water | Slate blue-gray | `#B8C5CE` | Muted, not bright blue — avoids competing with data |
| Borders/boundaries | Warm gray | `#9A9385` | Subtle, not distracting |
| Labels (place names) | Dark sepia | `#4A4238` | Legible but not harsh black |
| Roads (if shown) | Light taupe | `#D1C8B8` | Very subtle, background element |

## Density Gradient

Sequential scheme: low density → high density, 6 steps.

| Level | Density | Color | Hex |
| --- | --- | --- | --- |
| 1 | Very low | Cream | `#F7F3E8` |
| 2 | Low | Warm sand | `#E8DCC8` |
| 3 | Medium-low | Tan | `#D4C4A8` |
| 4 | Medium-high | Ochre | `#B89F72` |
| 5 | High | Sienna | `#8B7355` |
| 6 | Very high | Deep brown | `#5C4A3D` |

This gradient is perceptually even (lightness decreases steadily) and avoids any hue that conflicts with cartographic conventions.

## Typography

| Use | Font | Weight | Color |
| --- | --- | --- | --- |
| Page/section headers | Crimson Text | 600 (Semi) | `#3D352C` (espresso) |
| "World" in logo | Inter | 500–600 | `#3D352C` |
| Body text | Inter | 400 | `#4A4238` |
| Data labels / metrics | JetBrains Mono | 400 | `#5C4A3D` |
| Map place names | Inter | 500 | `#4A4238` |

## Accent Colors (UI)

For interactive elements — keeps the green identity in the UI chrome while the map stays neutral/sepia.

| Use | Color | Hex |
| --- | --- | --- |
| Primary accent (buttons, links) | Muted forest green | `#4A6741` |
| Hover/active state | Darker green | `#3A5233` |
| Selection highlight | Pale sage | `#D4DED0` |

## Font Sources

All fonts available from [Bunny Fonts](https://fonts.bunny.net) to avoid Google services:

- Crimson Text
- Inter
- JetBrains Mono
---
title: "Bertaud Radial Density Profiles"
modalTitle: "Radial Density Profile"
parentPage: "/methodology"
dataset: "urban-world-v1"
---

# Radial Density Profiles

Radial density profiles follow the method developed by Alain Bertaud to characterize the spatial structure of cities. They measure how population density varies with distance from the city centre.

## Method

1. **Centre identification** — the population-weighted centroid of each city is computed from H3 cells
2. **Ring construction** — concentric rings of 1 km width are drawn outward from the centre
3. **Density aggregation** — for each ring, we compute the average population density (persons/km²) of all H3 cells whose centroids fall within the ring
4. **Profile output** — the result is a distance-density curve that reveals whether a city is monocentric (steep gradient), polycentric (multiple peaks), or dispersed (flat profile)

## Why H3?

Radial profiles use the H3 hexagonal grid (resolution 8, ~0.74 km² per cell) rather than the regular 1 km grid. H3 cells have uniform area and compact shape, which reduces edge effects when assigning cells to distance rings.

## Interpretation

- **Steep exponential decay** — classic monocentric city (e.g., Paris, Buenos Aires)
- **Plateau then drop** — large dense core (e.g., Mumbai, Dhaka)
- **Multiple peaks** — polycentric structure (e.g., Ruhr area, Randstad)
- **Flat profile** — dispersed, low-density sprawl (e.g., Atlanta, Houston)

## The Standard Urban Model line

The dashed line on the chart is the **Standard Urban Model** — the classic monocentric baseline from urban economics (Alonso–Muth–Mills). It assumes density falls off smoothly from a single centre, following a simple curve:

`density(r) = D₀ × e^(−β · r)`

where _D₀_ is the density at the centre, _r_ is the distance from the centre, and _β_ (beta) is how quickly density drops as you move outward. We fit this curve to each city's observed profile, for every epoch from 1975 to 2030. The dashed line is that fitted curve; the solid line is what the city actually looks like. Comparing the two is the whole point — the gap between them is the city's deviation from the textbook.

We translate the two fitted numbers into two plain-language labels.

### Compactness — from β

A larger _β_ means density falls off faster, so the city is more **compact** (think Paris); a smaller _β_ means a flatter, more **spread** profile (think Atlanta). The bands are calibrated to the real distribution of fits across the world's cities, so they split it into roughly even thirds:

- **Compact** — β ≥ 0.37
- **Moderate** — 0.18 ≤ β < 0.37
- **Spread** — β < 0.18

These bands are fixed, so a city's label only changes when the city itself changes — not relative to whichever other cities are on screen.

### Structure — from R²

_R²_ measures how well the single-centre curve fits the real profile. A high _R²_ means the city really does look like one centre with density falling away; a low _R²_ means it doesn't.

- **Single-center** — R² ≥ 0.90
- **Multi-centered / Irregular** — R² < 0.90

**A poor fit tells you only that the textbook single-centre curve doesn't describe this city — never _why_.** The deviation could come from geography (a coast or mountains), several business districts, planning history, or data limits. We deliberately never assert a cause.

### When we show nothing — "fit not reliable here"

For some cities the exponential fit is meaningless: coastal or clipped cities with only a sliver of rings, very small urban areas, or places where density actually rises with distance (an inverted gradient that the single-centre model cannot describe). Rather than print a confident-but-wrong label, we suppress the dashed line, the badge, and the ranking entry and show **"fit not reliable here"**. The observed density line is always shown. A fit is treated as reliable only when it has at least **5 populated rings**, an **R² of at least 0.2** (below that the curve explains too little to trust at all), and a **positive gradient** (density falling outward). About **45% of all city-epochs** clear this bar. In the rankings, unreliable cities are excluded from the Compactness and Monocentricity sorts for that epoch.

> The bands above are calibrated against the full distribution of fits (≈46,000 reliable city-epochs across 1975–2030). The compactness and structure thresholds all live in a single place in the code, so any future recalibration stays consistent across the badge, the comparison table, and the rankings.

::citation-card{author="Bertaud, A." year="2018" title="Order without Design: How Markets Shape Cities" url="https://mitpress.mit.edu/books/order-without-design"}
::

---
title: "Bertaud Radial Density Profiles"
modalTitle: "Radial Density Profile"
parentPage: "/methodology"
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

::citation-card{author="Bertaud, A." year="2018" title="Order without Design: How Markets Shape Cities" url="https://mitpress.mit.edu/books/order-without-design"}
::

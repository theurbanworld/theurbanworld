---
title: "Urban World v1"
modalTitle: "Dataset: Urban World v1"
parentPage: "/data"
dataset: "urban-world-v1"
---

# Urban World v1

**Urban World v1** is a curated analytical dataset built on top of the Global Human Settlement Layer (GHSL). It uses H3 Resolution 8 hexagons as its spatial unit and applies additional processing to produce clean, reliable urban statistics.

## What it includes

- **H3 R8 population grid** — GHSL population values reaggregated onto Uber's H3 hexagonal grid at resolution 8 (~0.74 km² per cell)
- **City population and density statistics** — per epoch, per city
- **Density outlier filtering** — statistical removal of cities with unrealistic density values caused by GHSL disaggregation artifacts
- **Radial density profiles** — Bertaud-style profiles measuring how density varies with distance from the city centre

## Spatial unit

H3 Resolution 8 hexagons. Each hexagon covers approximately 0.74 km², providing globally consistent spatial units with uniform adjacency properties.

## Temporal coverage

12 epochs: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030.

## Methodology

See [Density Outlier Filtering](/methodology/density-outliers) and [Radial Density Profiles](/methodology/bertaud-radial) for detailed descriptions of the analytical methods applied to this dataset.

## Source data

Urban World v1 is derived from [GHSL R2023A](/data/source-ghsl). The raw raster data is reprojected, reaggregated onto H3 cells, and then processed through the Urban World pipeline.

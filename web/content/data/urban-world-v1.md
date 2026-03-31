---
title: "Urban World v1"
modalTitle: "Dataset: Urban World v1"
parentPage: "/data"
dataset: "urban-world-v1"
---

# Urban World v1

**Urban World v1** is a curated analytical dataset built on top of the Global Human Settlement Layer (GHSL). It uses H3 Resolution 8 hexagons as its spatial unit and applies additional processing to produce clean, reliable urban statistics.

## What it includes

- **Global H3 R8 population grid** — GHSL population values reaggregated onto Uber's H3 hexagonal grid at resolution 8 (~0.74 km² per cell) using area-weighted extraction (exactextract) for the entire world
- **City population and density statistics** — per epoch, per city, with birth and death year tracking
- **City emergence narratives** — proto-city population data for epochs before a city is classified as an urban center, and post-city data for cities that fall below the threshold
- **Per-city H3 heatmaps** — population per H3 cell within a 30 km buffer zone around each city, visible across all epochs
- **Density outlier filtering** — statistical removal of cities with unrealistic density values caused by GHSL disaggregation artifacts
- **Radial density profiles** — Bertaud-style profiles measuring how density varies from a population-weighted H3 centroid that updates per epoch

## Spatial unit

H3 Resolution 8 hexagons. Each hexagon covers approximately 0.74 km², providing globally consistent spatial units with uniform adjacency properties.

## Temporal coverage

12 epochs: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030.

## City lifecycle

GHSL defines urban centers using population and built-up area thresholds. Cities are born when a cluster of cells first meets the criteria, and can die if they later fall below it.

- **Birth year** — the first epoch where the city is classified as an urban center (from MTUC year-of-birth)
- **Death year** — the first epoch after the city's last appearance in the MTUC boundary dataset
- **Proto-city data** — for cities born after 1975, we show the population accumulating in the area that will become the city, using the birth-year boundary projected back in time
- **Post-city data** — for cities that disappear, we continue tracking population in the last-known boundary

## Methodology

See [Density Outlier Filtering](/methodology/density-outliers) and [Radial Density Profiles](/methodology/bertaud-radial) for detailed descriptions of the analytical methods applied to this dataset.

## Source data

Urban World v1 is derived from [GHSL R2023A](/data/source-ghsl). The raw raster data is reprojected, reaggregated onto H3 cells using area-weighted extraction (exactextract), and then processed through the Urban World pipeline.

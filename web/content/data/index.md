---
title: Data
---

# Datasets

The Urban World provides two datasets for exploring global urbanization. Each dataset uses a different spatial representation and level of curation.

## Available datasets

- **[Urban World v1](/data/urban-world-v1)** — a curated dataset using H3 hexagonal grids with city emergence narratives, per-cell population heatmaps, outlier filtering, and radial density profiles
- **[GHSL R2024](/data/ghsl-r2024)** — the raw Global Human Settlement Layer on its native 1 km grid, presented without filtering

## Pipeline overview

Raw raster data is downloaded from the GHSL, reprojected, and aggregated into these datasets:

::pipeline-diagram
::

## Source data

Both datasets are derived from the [Global Human Settlement Layer (GHSL)](/data/source-ghsl) produced by the European Commission's Joint Research Centre.

---
title: Data
---

# Data Sources

The Urban World draws on satellite-derived, globally consistent datasets to measure urbanization. This page describes each data source, how we process it, and what it measures.

## Pipeline overview

Raw raster data is downloaded, reprojected, and aggregated into two canonical datasets:

- **GHSL Grid 1 km** — population and built-up area on a regular 1 km Mollweide grid
- **GHSL H3 Resolution 8** — the same variables reaggregated onto Uber's H3 hexagonal grid

Both datasets cover seven epochs: 1975, 1980, 1990, 2000, 2005, 2010, 2015, 2020, 2025, and 2030.

::pipeline-diagram
::

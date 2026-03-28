---
title: Methodology
---

# Methodology

This page describes the analytical methods used to transform raw satellite data into the statistics and visualizations shown on The Urban World.

## City definitions

Cities are defined using the GHSL Urban Centre Database (GHS-UCDB), which delineates functional urban areas based on population density contiguity rules. Each urban centre has a unique boundary polygon used to clip raster data.

## Population and density

For each city and epoch, we sum population grid cells (GHS-POP) falling within the city boundary to get total population. Density is computed as population divided by the built-up area (GHS-BUILT-S) within the boundary.

## Rankings

City rankings are computed per epoch. Population rank orders cities by total population. Density rank uses population-weighted density to avoid distortion from low-density periphery cells.

## Density outlier filtering

Some cities in the GHSL/UCDB dataset have unrealistically high densities caused by population disaggregation artifacts in small city boundaries. We use a median-based statistical filter to exclude these from rankings and exports. See [Density Outlier Filtering](/methodology/density-outliers) for details and a full list of excluded cities.

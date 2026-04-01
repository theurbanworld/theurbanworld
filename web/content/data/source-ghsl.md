---
title: "GHSL — Global Human Settlement Layer"
modalTitle: "Source: GHSL"
parentPage: "/data"
---

# Global Human Settlement Layer (GHSL)

The **Global Human Settlement Layer** is produced by the European Commission's Joint Research Centre (JRC). It provides global, open, multi-temporal data on human presence on Earth.

## What it measures

- **GHS-POP** — population distribution grids (residents per cell)
- **GHS-BUILT-S** — built-up surface area (square meters of built footprint per cell)

Both products are available at 1 km and 100 m resolution, in the Mollweide equal-area projection.

## Temporal coverage

GHSL R2023A provides data for 12 epochs: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, and 2030. The 2025 and 2030 epochs are model-based projections.

## How we use it

We download the 1 km resolution GHS-POP rasters in WGS84 projection (30 arc-second) and process the entire world into H3 Resolution 8 hexagons using area-weighted extraction (exactextract). This produces a global population timeseries of ~57 million H3 cells across 12 epochs.

From this global dataset we derive per-city statistics, population heatmaps with 30 km buffer zones, proto-city emergence data, and Bertaud-style radial density profiles using per-epoch population-weighted centroids.

City boundaries and birth years come from the **GHSL Urban Centre Database (UCDB)** and its **Multi-Temporal Urban Centre (MTUC)** boundaries, which track how each city's footprint changes across epochs.

::citation-card{author="Schiavina, M., Freire, S., Carioli, A., MacManus, K." year="2023" title="GHS-POP R2023A" url="https://ghsl.jrc.ec.europa.eu/ghs_pop2023.php"}
::

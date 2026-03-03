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

GHSL R2023A provides data for epochs: 1975, 1980, 1990, 2000, 2005, 2010, 2015, 2020, 2025, and 2030. The 2025 and 2030 epochs are model-based projections.

## How we use it

We download the 1 km resolution GHS-POP and GHS-BUILT-S rasters, extract values for each city's extent, and aggregate them into population, density, and area statistics.

::citation-card{author="Schiavina, M., Freire, S., Carioli, A., MacManus, K." year="2023" title="GHS-POP R2023A" url="https://ghsl.jrc.ec.europa.eu/ghs_pop2023.php"}
::

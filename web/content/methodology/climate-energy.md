---
title: "Climate & Energy Profile"
modalTitle: "Climate & Energy"
parentPage: "/methodology"
---

# Climate & Energy Profile

The **Climate & Energy** profile surfaces the energy- and climate-relevant attributes already carried in the **GHSL Urban Centre Database (UCDB) R2024A** — heat and flood exposure, solar and wind resource, carbon footprint, greenness, urban form, and hazard occurrence. No new data is downloaded; the pipeline simply stops discarding attributes it already extracts.

Four headline metrics lead — **heat** (warm days), **flood** (population in the 100-year flood zone), **solar** (PV potential), and **per-capita carbon** — with the remaining metrics organised by lens as supporting depth.

## Three temporal classes

Each metric renders according to what its data actually supports:

- **Time series** — values on the metric's own year axis (e.g. emissions 1975–2020, UTCI 1970–2020, greenness 1985–2025). These render on their native spine, *not* the population epoch slider, so no data point is implied where none exists.
- **Projections** — a present value and a modelled future value (e.g. warm days today vs end-century SSP5-8.5, Köppen class today vs 2071–2099). Shown as a now/future toggle, never interpolated into a trend.
- **Snapshots** — a single climatological value with no implied trend (e.g. solar PV potential, wind speed, canopy height).

## Modeled, not measured

Several metrics are **model outputs**, not direct observations, and carry a visible "modeled, not measured" qualifier:

- **Emissions** (EDGAR) allocate national totals to space using population and built-up surface, so per-capita CO₂ is partly circular with the population layer. We always show per-capita CO₂ together with its **sector fingerprint** (energy / transport / industry / residential) — the least population-circular signal — so readers see what drives the number.
- **Projections** (warm days, mean temperature, Köppen class) are scenario-based futures, not forecasts.
- **Exposure and hazard models** (flood, coastal, cyclone) come from return-period hazard modelling.

The observatory contextualises energy and climate; it is descriptive and comparative, not an insurance-grade risk-scoring product. Divergent emissions estimates are shown side by side, never averaged into a single "true" number.

## Coverage

UCDB covers roughly 11,400 of the ~13,000 urban centres in the observatory. Cities outside UCDB, and marine metrics for inland cities, render a graceful "not available for this city" state rather than a guess.

::citation-card{author="Melchiorri, M., et al." year="2024" title="Stats in the City — the GHSL Urban Centre Database 2025 (GHS-UCDB R2024A)" url="https://ghsl.jrc.ec.europa.eu/ucdb2024.php"}
::

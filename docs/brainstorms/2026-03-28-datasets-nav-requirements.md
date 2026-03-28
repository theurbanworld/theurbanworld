---
date: 2026-03-28
topic: datasets-nav-redesign
---

# Datasets & Navigation Redesign

## Problem Frame

The current UI presents Grid 1km vs H3 R8 as a low-level spatial toggle, but they actually represent fundamentally different things: raw upstream data (GHSL on its native grid) vs a curated analytical product (Urban World, built on H3). This distinction is invisible to users. Epoch selection and global stats are buried in a floating panel that competes with the map. The "Cities" button is redundant since rankings is already the default view.

## Requirements

**Dataset Model**

- R1. Introduce a "dataset" abstraction that replaces the Grid/H3 toggle. Each dataset bundles: a name, version label, spatial representation, available epochs, city list, and associated methodologies.
- R2. Ship with two datasets: "GHSL R2024" (raw Grid 1km data, no outlier filtering) and "Urban World v1" (curated H3 R8 data with outlier filtering, the default).
- R3. Version is displayed in the dataset name for transparency but users cannot switch between versions — only the latest is available.
- R4. Methodologies are tied to datasets. For now, all methodology pages (density outliers, radial profiles) apply only to "Urban World". GHSL R2024 has no methodology layer.
- R5. Each dataset has its own content page under `/data/` (e.g. `/data/ghsl-r2024`, `/data/urban-world-v1`) documenting its sources, processing, and characteristics.

**Navigation Restructure**

- R6. Replace the "Cities" button in the search strip with a dataset dropdown selector (left side of strip).
- R7. The dataset dropdown shows all available datasets, the currently selected one, and an info link (e.g. small icon) per dataset that navigates to its `/data/` subpage.
- R8. The search bar remains centered in the strip.
- R9. The selected epoch year displays on the right side of the strip (compact, read-only display).
- R10. Remove the "Cities" button entirely. The logo/home link in the header serves as the way back to rankings.

**Eyebrow Panel**

- R11. Replace the current floating `GlobalContextPanel` (top-right) with an "eyebrow" panel that drops down from the right side of the strip, below the epoch year display.
- R12. The eyebrow is ~250-300px wide, always visible, and contains: the epoch slider, world population, and urban population stats.
- R13. The sidebar remains on the left at its current width.

**Dataset Switching Behavior**

- R14. When switching datasets, attempt to stay on the same city if it exists in the new dataset. Fall back to the rankings view if the city is not present.
- R15. Epoch selection resets to the new dataset's default epoch (or nearest available) if the current epoch is not available in the target dataset.

## Success Criteria

- Users can explore raw GHSL data without Urban World's curation applied, and understand they are looking at a different dataset.
- The epoch slider and global stats are always accessible without obscuring the map.
- Adding a new dataset in the future requires defining its config + data files + content page — no structural UI changes.

## Scope Boundaries

- No version switching UI — version is display-only.
- No methodology changes — existing methodology content stays as-is, just gets scoped to Urban World.
- No new datasets beyond GHSL R2024 and Urban World v1 in this iteration.
- The pipeline is out of scope — this is frontend only. Data files for GHSL raw (Grid 1km) already exist.

## Key Decisions

- **"Dataset" as the user-facing term**: simple, familiar, chosen over "data package", "collection", "source".
- **Grid vs H3 is a dataset-level concern, not a user toggle**: GHSL R2024 is grid-based, Urban World v1 is H3-based. The spatial representation is a property of the dataset, not a separate choice.
- **"Cities" button removed**: the home/rankings view is the default; the logo serves as nav home.
- **Eyebrow panel always visible**: compact enough to stay open, no toggle needed.
- **Dataset dropdown with info links**: each dataset in the dropdown has a link to its documentation page.

## Dependencies / Assumptions

- Grid 1km data files (PMTiles boundaries, city populations JSON) are already generated and available on R2.
- GHSL R2024 uses the same epoch range (1975-2030) as Urban World v1.

## Outstanding Questions

### Deferred to Planning

- [Affects R1][Technical] How should the dataset config be structured? (inline TypeScript config vs JSON file vs content collection)
- [Affects R2][Needs research] Does the Grid 1km data currently support all the same city-level features (rankings, city detail panels), or are some features H3-only?
- [Affects R11-R12][Technical] Should the eyebrow panel be a separate component or part of the map overlay system?
- [Affects R4][Technical] How should methodology pages indicate which dataset they apply to? (frontmatter metadata, conditional rendering, or separate pages per dataset)

## Next Steps

→ `/ce:plan` for structured implementation planning

---
title: "Density Outlier Filtering"
parentPage: "/methodology"
---

# Density Outlier Filtering

Some cities in the GHSL/UCDB dataset report unrealistically high population densities. These are not the world's densest cities — they are data artifacts caused by how satellite-derived population estimates interact with small city boundaries.

## The problem

GHSL assigns population to ~1 km grid cells using satellite-detected built-up area and census disaggregation. When a city in the Urban Centre Database (UCDB) has a very small boundary polygon, it captures only a handful of these cells. If those cells happen to sit near a larger city's dense core, the population attributed to them can be disproportionately high, producing densities 2--5x higher than the densest real cities.

For example, a city boundary covering just 6 H3 cells (~4.4 km^2^) might report a density of 45,000 people/km^2^ — far exceeding Mumbai (~28,000/km^2^), the densest major city with over 1,000 cells of consistent data.

## Filtering approach

We use a **median-based two-tier filter** to identify and exclude these artifacts from rankings and web exports. The filter computes each city's **median density** and **median cell count** across all 12 epochs (1975--2030), then applies two rules:

- **Tier 1 — Tiny cities**: median cell count below 5 (~3.7 km^2^ for H3). Cities that are persistently this small across five decades of data lack enough spatial coverage for any meaningful density estimate. They are always excluded.
- **Tier 2 — Small + dense**: median cell count below 50 (~37 km^2^) **and** median density above 20,000 people/km^2^. Cities that are consistently small and claim to be denser than the world's largest megacities are implausible — real cities at these densities have hundreds or thousands of cells.

### Why medians?

Earlier versions of this filter checked whether a city triggered the outlier criteria at *any* epoch. This produced false positives for cities that were genuinely small in 1975 (when GHSL resolution was lower) but grew into legitimate urban areas by 2025. For example, Bajitpur in Bangladesh had just 4 cells in 1975 but 229 cells and 507,000 people by 2025.

Using medians across all epochs smooths out this early-epoch noise. A city is only excluded if it is *persistently* too small or *persistently* too dense — not because of a single noisy data point decades ago.

### Where the filter is applied

- **Rankings** — outliers are excluded before computing population, density, and growth rankings
- **City index** — outliers are excluded from the search index
- **City population exports** — outliers are excluded from the JSON files served to the frontend

Raw population data files (`city_populations_*.parquet`) are preserved unfiltered for research use.

## Excluded cities

The filter currently excludes **59 cities** out of 11,422 (0.5%). The table below lists all excluded cities, sorted by median density.

### Tier 2 — Small + dense (38 cities)

Cities with fewer than 50 median cells and median density above 20,000/km^2^.

| City | Country | Population (2025) | Median density | Median cells |
|------|---------|------------------:|---------------:|-------------:|
| Tiquisio | Colombia | 196,519 | 45,045 | 6 |
| Sarvestan | Iran | 957,483 | 42,369 | 19 |
| Safipur | India | 54,690 | 33,318 | 5 |
| Pingchang County | China | 129,635 | 31,844 | 5 |
| Shelepino | Russia | 123,131 | 30,706 | 7 |
| Bangarmau | India | 84,597 | 30,288 | 9 |
| Narus | South Sudan | 251,066 | 29,798 | 9 |
| Sandila | India | 102,087 | 29,514 | 10 |
| Sareyn | Iran | 367,689 | 29,158 | 12 |
| Jalesar | India | 59,628 | 27,723 | 5 |
| Bolo | Nigeria | 109,469 | 26,978 | 6 |
| Togechane | Ethiopia | 202,792 | 26,865 | 9 |
| Nimule | South Sudan | 628,621 | 26,634 | 18 |
| Hardoi | India | 441,914 | 25,860 | 32 |
| Betou | Republic of the Congo | 293,974 | 25,412 | 12 |
| Kharameh | Iran | 925,847 | 23,874 | 35 |
| Uige | Angola | 219,879 | 23,798 | 42 |
| Al Masaliyah | Yemen | 120,646 | 23,736 | 5 |
| Qaraziadin | Iran | 216,435 | 23,134 | 9 |
| Filtu | Ethiopia | 131,619 | 22,815 | 5 |
| Adan Barakah | Yemen | 102,053 | 22,687 | 5 |
| Bugama | Nigeria | 216,856 | 22,667 | 10 |
| Ghatampur | India | 78,132 | 22,547 | 6 |
| Keren | Eritrea | 234,158 | 22,094 | 18 |
| Sikandra Rao | India | 90,827 | 22,016 | 8 |
| Sherkot | India | 92,753 | 21,322 | 5 |
| Sakju | North Korea | 52,387 | 21,285 | 5 |
| Pinillos | Colombia | 107,332 | 21,184 | 7 |
| Badaun | India | 357,237 | 21,144 | 18 |
| Koksan | North Korea | 87,953 | 21,123 | 8 |
| Kebkabiya | Sudan | 683,642 | 20,619 | 18 |
| Dharwad | India | 897,464 | 20,600 | 42 |
| Fik' | Ethiopia | 159,040 | 20,452 | 7 |
| Dir | Pakistan | 68,683 | 20,423 | 5 |
| As Sayyid | Yemen | 235,096 | 20,298 | 10 |
| Mamrezpur Al | India | 53,833 | 20,280 | 6 |
| Mawlamyinegyunn | Myanmar | 175,796 | 20,151 | 10 |
| Jalalabad | India | 79,065 | 20,046 | 10 |

### Tier 1 — Tiny cities (21 cities)

Cities with fewer than 5 median cells across all epochs.

| City | Country | Population (2025) | Median density | Median cells |
|------|---------|------------------:|---------------:|-------------:|
| (unnamed) | Madagascar | 20,832 | 26,890 | 1 |
| Phuntsholing | Bhutan | 73,971 | 24,532 | 4 |
| Yiliang | China | 61,483 | 20,642 | 4 |
| Jamame | Somalia | 88,127 | 19,875 | 4 |
| Garhmuktesar | India | 63,933 | 18,433 | 4 |
| Kitotolo | Democratic Republic of the Congo | 71,891 | 18,394 | 4 |
| Anupshahr | India | 42,327 | 17,356 | 4 |
| Masisi | Democratic Republic of the Congo | 57,786 | 17,320 | 4 |
| Qarabag | Afghanistan | 42,445 | 17,262 | 3 |
| Songwe | Democratic Republic of the Congo | 37,428 | 16,216 | 3 |
| Sahabad | India | 39,614 | 15,613 | 2 |
| Biala | Egypt | 55,649 | 15,593 | 4 |
| Siyana | India | 50,957 | 15,296 | 4 |
| Mutombo-Lamata | Democratic Republic of the Congo | 39,922 | 14,523 | 3 |
| Gangoh | India | 42,496 | 13,854 | 4 |
| Sharaqpur | Pakistan | 44,517 | 13,825 | 4 |
| Soku | Nigeria | 26,916 | 13,800 | 3 |
| Chodavaram | India | 42,280 | 13,576 | 4 |
| Miezi | Mozambique | 36,769 | 11,633 | 4 |
| Alanda | India | 31,087 | 10,704 | 4 |
| Behea | India | 37,128 | 10,141 | 4 |

## Geographic patterns

The excluded cities are concentrated in regions where GHSL disaggregation is least reliable:

- **India** (16 cities) — high population density near small UCDB boundaries
- **Iran** (4 cities) — small satellite cities near major urban cores
- **Democratic Republic of the Congo** (4 cities) — sparse built-up area data
- **South Sudan, Sudan, Yemen, North Korea** — limited ground-truth data for census disaggregation

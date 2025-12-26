"""
06 - Compute Bertaud-style radial density profiles.

Purpose: Calculate population density at 1km intervals from city center
Input:
  - data/interim/cities.parquet
  - data/processed/h3_tiles/h3_r9_pop_2025.parquet
  - data/interim/city_boundaries/{city_id}.parquet
Output:
  - data/interim/radial_profiles/{city_id}.json
  - data/interim/radial_profiles/_all_profiles.parquet

Decision log:
  - Use population-weighted centroid from boundary extraction
  - 50 rings at 1km intervals (0-50km)
  - Use H3 res-9 cells (same as boundaries for consistency)
  - Calculate actual area per ring (handles partial/coastal rings)
  - Fit log-linear gradient for urban form classification
Date: 2024-12-08
"""

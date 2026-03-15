# In `/pipeline`
- All Python commands should be run with `uv run`
- Use DuckDB cli for data exploration: `duckdb`

## Running pipeline scripts

Scripts are organized by domain under `src/`:

```bash
# Download
uv run python -m src.download.download_ghsl
uv run python -m src.download.download_h3_r8

# Cities
uv run python -m src.cities.extract_attributes extract
uv run python -m src.cities.extract_geometries
uv run python -m src.cities.generate_cities
uv run python -m src.cities.compute_populations --source h3-r8
uv run python -m src.cities.compute_populations --source grid-1km
uv run python -m src.cities.compute_rankings --source h3-r8
uv run python -m src.cities.compute_rankings --source grid-1km

# Grid
uv run python -m src.grid.extract_grid_1km
uv run python -m src.grid.extract_grid_1km --epoch 2025  # single epoch

# H3
uv run python -m src.h3.merge_h3_r8_timeseries --local
uv run python -m src.h3.load_h3_r8_to_psql

# Radial (H3 only)
uv run python -m src.radial.generate_radial_profiles

# Tiles
uv run python -m src.tiles.generate_boundaries --local
uv run python -m src.tiles.generate_grid_1km_outlines --local
uv run python -m src.tiles.generate_h3_r8_outlines --local
uv run python -m src.tiles.generate_font_glyphs --local
uv run python -m src.tiles.generate_hover_sprites --local

# Web export (JSON for frontend)
uv run python -m src.web_export.generate_city_index --local
uv run python -m src.web_export.generate_city_populations --source h3-r8 --local
uv run python -m src.web_export.generate_city_populations --source grid-1km --local
uv run python -m src.web_export.generate_radial_profiles --local
uv run python -m src.web_export.generate_city_cells --local

# Analyze density outliers
uv run python -m src.cities.density_outliers --source h3-r8

# Validate
uv run python -m src.validate.validate_cities --source h3-r8 -v
uv run python -m src.validate.validate_cities --source grid-1km -v

# Explore (Streamlit)
uv run streamlit run src/explore/app_explore.py
```

## Two Canonical Datasets

The pipeline produces **two canonical population datasets**:

1. **`ghsl-grid-1km`** — Pure GHSL raster pixels within city boundaries (1 km² each)
2. **`ghsl-h3-r8`** — H3 hexagonal grid derived from GHSL (0.55-0.74 km² per cell)

Scripts that accept `--source` (`h3-r8` or `grid-1km`):
- `compute_populations` — city-level population aggregation
- `compute_rankings` — rankings, growth, density peers
- `generate_city_populations` — JSON export for frontend
- `validate_cities` — data validation

Output files include the source in their name: `city_populations_h3_r8.parquet`, `city_populations_grid_1km.parquet`, etc.

## Density Outlier Filtering

Some GHSL/UCDB cities have unrealistically high densities — small boundary areas with
concentrated population estimates that exceed any real-world city. These are filtered
from rankings and web exports (but preserved in raw `city_populations` parquet files).

**Module**: `src/cities/density_outliers.py`

**Criteria** (two-tier filter, a city is excluded if ANY epoch triggers either):
- Tier 1: `cell_count < 5` — tiny cities always excluded (~3.7 km² for H3-R8)
- Tier 2: `cell_count < 50 AND density_per_km2 > 25,000` — small cities with implausibly high density

**Where applied**:
- `compute_rankings` — outliers excluded before computing all rankings
- `generate_city_populations` — outliers excluded from frontend JSON
- `generate_city_index` — outliers excluded from city search index

**Analysis tool**:
```bash
uv run python -m src.cities.density_outliers --source h3-r8
uv run python -m src.cities.density_outliers --source h3-r8 --tiny-cells 10 --small-cells 100
uv run python -m src.cities.density_outliers --source h3-r8 --report  # writes JSON report
```

**Report**: `--report` writes `data/processed/cities/density_outliers_report.json` listing
every excluded city with its name, country, density, population, area, cell count, and
exclusion reason. Run this after `compute_populations` to produce an auditable record.

## Data Validation

Run validation after any pipeline changes:
```bash
uv run python -m src.validate.validate_cities --source h3-r8
uv run python -m src.validate.validate_cities --source h3-r8 -v  # verbose mode
```

### Adding or Changing Output Data

When modifying pipeline scripts that produce parquet files in `data/processed/cities/`:

1. **Update the Pandera schema** in `src/validate/validate_cities.py`:
   - Add/modify the `DataFrameModel` class for the affected table
   - Use proper types: `str`, `int`, `float` with `Field()` constraints
   - Set `nullable=True` for columns that can have NULL values
   - Add range constraints: `ge=`, `le=`, `gt=`, `lt=` for numeric bounds

2. **Add cross-table validation** if needed:
   - Foreign key checks go in `check_foreign_keys()`
   - New data quality checks get their own function
   - Call the new check in `main()` under "Data Quality Checks"

3. **Run validation** to verify the schema matches actual data

### Known Data Issues (as of 2025-12-27)

| Issue | Cause | Future Fix |
|-------|-------|------------|
| 11 duplicate city_ids | Border cities in multiple countries | Deduplicate in cities/generate_cities |
| 2,648 orphaned city_ids | MTUC vs UCDB city list mismatch | Use UCDB as canonical source |
| 61% NULL growth metrics | Cities didn't exist in 1975 | Expected, document only |
| 19% NULL peer_names | Name lookup failures | Join from cities.parquet |
| Density outliers | Small UCDB boundaries with few cells get inflated densities | Filtered in rankings/export (see density_outliers.py) |

### Validation Schema Reference

```
cities.parquet                       -> CitySchema
city_populations_{source}.parquet    -> CityPopulationSchema
city_rankings_{source}.parquet       -> CityRankingSchema
city_growth_{source}.parquet         -> CityGrowthSchema
city_density_peers_{source}.parquet  -> CityDensityPeersSchema
radial_profiles_h3_r8.parquet       -> RadialProfileSchema
```

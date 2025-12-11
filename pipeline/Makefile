# Urban Data Pipeline - Makefile
#
# Purpose: Orchestrate the GHSL data processing pipeline
# Usage:
#   make all          - Run full pipeline
#   make test-cities  - Run pipeline for test cities only (fast iteration)
#   make status       - Show pipeline progress
#   make clean        - Remove all generated data
#
# Decision log:
#   - Using file-based targets for Make dependency tracking
#   - Each phase creates a sentinel file on completion
#   - test-only flag enables fast iteration during development
# Date: 2024-12-08

.PHONY: all clean download extract-ucdb extract convert-100m convert-1km boundaries radial export context test-cities status lint test help basemap basemap-force basemap-info upload upload-dry upload-force upload-basemap upload-data r2-cors explore

# Default target
all: context basemap

# Python environment
PYTHON := uv run python
UV := uv

# Data directories
RAW_DIR := data/raw
INTERIM_DIR := data/interim
PROCESSED_DIR := data/processed

# Basemap files
BASEMAP_DIR := $(PROCESSED_DIR)/basemap
BASEMAP_FILE := $(BASEMAP_DIR)/planet.pmtiles
BASEMAP_META := $(BASEMAP_DIR)/metadata.json

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

.venv: pyproject.toml
	$(UV) venv
	$(UV) sync
	touch $@

setup: .venv
	@echo "Environment ready. Run 'make download' to start the pipeline."

# ============================================================================
# DOWNLOAD PHASE
# ============================================================================

$(RAW_DIR)/.download_complete: .venv
	$(PYTHON) -m src.s01_download_ghsl
	touch $@

download: $(RAW_DIR)/.download_complete
	@echo "Download complete."

# ============================================================================
# UCDB EXTRACTION PHASE
# ============================================================================

# Full UCDB extraction (schema + themes + geometries + urban centers)
$(INTERIM_DIR)/ucdb/.extract_complete: $(RAW_DIR)/.download_complete .venv
	$(PYTHON) -m src.s02_extract_ucdb all
	touch $@

# For backwards compatibility
$(INTERIM_DIR)/cities.parquet: $(INTERIM_DIR)/ucdb/.extract_complete

extract-ucdb: $(INTERIM_DIR)/ucdb/.extract_complete
	@echo "UCDB extraction complete."

extract: extract-ucdb
	@echo "Urban centers extracted."

# ============================================================================
# H3 CONVERSION PHASE
# ============================================================================

# 100m raster to H3 (2020 only)
$(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet: $(RAW_DIR)/.download_complete $(INTERIM_DIR)/cities.parquet .venv
	$(PYTHON) -m src.s03_raster_to_h3_100m

convert-100m: $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet
	@echo "100m H3 conversion complete."

# 1km raster to H3 (time series) - uses Modal cloud
$(INTERIM_DIR)/h3_pop_1km/time_series.parquet: $(RAW_DIR)/.download_complete .venv
	uv run modal run src/s04_raster_to_h3_1km_modal.py

convert-1km: $(INTERIM_DIR)/h3_pop_1km/time_series.parquet
	@echo "1km H3 conversion complete."

# Both conversions
convert: convert-100m convert-1km

# ============================================================================
# CITY ANALYSIS PHASE
# ============================================================================

# City boundary extraction
$(INTERIM_DIR)/city_boundaries/.complete: $(INTERIM_DIR)/cities.parquet $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet .venv
	$(PYTHON) -m src.s05_extract_city_boundaries
	touch $@

boundaries: $(INTERIM_DIR)/city_boundaries/.complete
	@echo "City boundaries extracted."

# Radial density profiles
$(INTERIM_DIR)/radial_profiles/.complete: $(INTERIM_DIR)/cities.parquet $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet .venv
	$(PYTHON) -m src.s06_compute_radial_profiles
	touch $@

radial: $(INTERIM_DIR)/radial_profiles/.complete
	@echo "Radial profiles computed."

# ============================================================================
# EXPORT PHASE
# ============================================================================

$(PROCESSED_DIR)/city_index.json: $(INTERIM_DIR)/cities.parquet \
                                   $(INTERIM_DIR)/h3_pop_1km/time_series.parquet \
                                   $(INTERIM_DIR)/city_boundaries/.complete \
                                   $(INTERIM_DIR)/radial_profiles/.complete \
                                   .venv
	$(PYTHON) -m src.s07_export_web_formats

export: $(PROCESSED_DIR)/city_index.json
	@echo "Web export complete. Data ready in $(PROCESSED_DIR)/"

# ============================================================================
# CONTEXT METRICS PHASE
# ============================================================================

# Compute global/continental/national rankings, growth metrics, density peers
$(PROCESSED_DIR)/cities/.context_complete: $(PROCESSED_DIR)/city_index.json .venv
	$(PYTHON) -m src.s08_compute_context_metrics
	touch $@

context: $(PROCESSED_DIR)/cities/.context_complete
	@echo "Context metrics computed."

# ============================================================================
# BASEMAP PHASE
# ============================================================================

# Download Protomaps planet basemap (~70GB)
$(BASEMAP_FILE): .venv
	$(PYTHON) -m src.s10_download_basemap

basemap: $(BASEMAP_FILE)
	@echo "Basemap ready."

# Force re-download even if file exists
basemap-force: .venv
	$(PYTHON) -m src.s10_download_basemap --force

# Show basemap metadata
basemap-info:
	@test -f $(BASEMAP_META) && cat $(BASEMAP_META) || echo "No metadata found. Run 'make basemap' first."

# ============================================================================
# R2 UPLOAD PHASE
# ============================================================================

# Upload all processed data to R2 (requires .env with R2 credentials)
upload: all .venv
	$(PYTHON) -m src.s20_upload_to_r2

# Preview what would be uploaded (dry run)
upload-dry: .venv
	$(PYTHON) -m src.s20_upload_to_r2 --dry-run

# Force full re-upload (ignore cache)
upload-force: .venv
	$(PYTHON) -m src.s20_upload_to_r2 --force

# Upload only basemap
upload-basemap: basemap .venv
	$(PYTHON) -m src.s20_upload_to_r2 --only basemap

# Upload only H3 and city data
upload-data: export .venv
	$(PYTHON) -m src.s20_upload_to_r2 --only h3 --only cities

# One-time CORS setup for R2 bucket
r2-cors: .venv
	$(PYTHON) -m src.s21_configure_r2_cors

# ============================================================================
# TEST CITIES (Fast iteration)
# ============================================================================

test-cities: .venv
	@echo "Running pipeline for test cities only..."
	$(PYTHON) -m src.s01_download_ghsl --test-only
	$(PYTHON) -m src.s02_extract_ucdb all
	$(PYTHON) -m src.s03_raster_to_h3_100m --test-only
	uv run modal run src/s04_raster_to_h3_1km_modal.py --test
	$(PYTHON) -m src.s05_extract_city_boundaries --test-only
	$(PYTHON) -m src.s06_compute_radial_profiles --test-only
	$(PYTHON) -m src.s07_export_web_formats --test-only
	$(PYTHON) -m src.s08_compute_context_metrics --test-only
	@echo "Test cities pipeline complete."

# ============================================================================
# DATA EXPLORATION
# ============================================================================

# Launch UCDB data explorer (Streamlit)
explore: $(INTERIM_DIR)/ucdb/.extract_complete .venv
	$(UV) run streamlit run src/s02a_explore_ucdb.py

# ============================================================================
# UTILITIES
# ============================================================================

# Show pipeline status
status:
	@echo "=== Pipeline Status ==="
	@echo "Download:   $$(test -f $(RAW_DIR)/.download_complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "UCDB:       $$(test -f $(INTERIM_DIR)/ucdb/.extract_complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "H3 100m:    $$(test -f $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet && echo 'COMPLETE' || echo 'PENDING')"
	@echo "H3 1km:     $$(test -f $(INTERIM_DIR)/h3_pop_1km/time_series.parquet && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Boundaries: $$(test -f $(INTERIM_DIR)/city_boundaries/.complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Radial:     $$(test -f $(INTERIM_DIR)/radial_profiles/.complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Export:     $$(test -f $(PROCESSED_DIR)/city_index.json && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Context:    $$(test -f $(PROCESSED_DIR)/cities/.context_complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Basemap:    $$(test -f $(BASEMAP_FILE) && echo 'COMPLETE' || echo 'PENDING')"

# Run tests
test: .venv
	$(UV) run pytest tests/ -v

# Lint and format
lint: .venv
	$(UV) run ruff check src/
	$(UV) run ruff format --check src/

format: .venv
	$(UV) run ruff format src/

# Type check
typecheck: .venv
	$(UV) run mypy src/

# Clean intermediate files only
clean-interim:
	rm -rf $(INTERIM_DIR)/*
	mkdir -p $(INTERIM_DIR)/{h3_pop_100m,h3_pop_1km,city_boundaries,radial_profiles}

# Clean processed files only
clean-processed:
	rm -rf $(PROCESSED_DIR)/*
	mkdir -p $(PROCESSED_DIR)/{h3_tiles,cities}

# Clean all generated data (keeps raw downloads)
clean: clean-interim clean-processed
	@echo "Cleaned interim and processed data. Raw downloads preserved."

# Clean everything including downloads
clean-all: clean
	rm -rf $(RAW_DIR)/*
	rm -rf .venv
	mkdir -p $(RAW_DIR)/{ghsl_pop_100m,ghsl_pop_1km,ucdb}
	@echo "All data cleaned."

# Help
help:
	@echo "Urban Data Pipeline - Available targets:"
	@echo ""
	@echo "  Setup:"
	@echo "    setup        - Create Python environment"
	@echo ""
	@echo "  Pipeline (run in order):"
	@echo "    download     - Download GHSL data from JRC"
	@echo "    extract-ucdb - Extract UCDB (schema, themes, geometries, urban centers)"
	@echo "    convert-100m - Convert 100m raster to H3"
	@echo "    convert-1km  - Convert 1km raster to H3 (time series)"
	@echo "    boundaries   - Extract city boundary H3 cells"
	@echo "    radial       - Compute radial density profiles"
	@echo "    export       - Export web-ready JSON/GeoParquet"
	@echo "    context      - Compute context metrics (rankings, growth, peers)"
	@echo ""
	@echo "  Basemap:"
	@echo "    basemap       - Download Protomaps planet PMTiles (~70GB)"
	@echo "    basemap-force - Force re-download basemap"
	@echo "    basemap-info  - Show basemap metadata"
	@echo ""
	@echo "  R2 Upload:"
	@echo "    upload        - Upload all processed data to R2"
	@echo "    upload-dry    - Preview what would be uploaded"
	@echo "    upload-force  - Force full re-upload (ignore cache)"
	@echo "    upload-basemap - Upload only basemap"
	@echo "    upload-data   - Upload only H3 and city data"
	@echo "    r2-cors       - One-time CORS setup for R2 bucket"
	@echo ""
	@echo "  Shortcuts:"
	@echo "    all          - Run full pipeline (default)"
	@echo "    test-cities  - Run pipeline for 6 test cities only"
	@echo "    convert      - Run both H3 conversions"
	@echo "    extract      - Alias for extract-ucdb"
	@echo ""
	@echo "  Data Exploration:"
	@echo "    explore      - Launch UCDB data explorer (Streamlit)"
	@echo ""
	@echo "  Utilities:"
	@echo "    status       - Show pipeline progress"
	@echo "    test         - Run pytest tests"
	@echo "    lint         - Run ruff linter"
	@echo "    format       - Format code with ruff"
	@echo "    clean        - Remove interim/processed data"
	@echo "    clean-all    - Remove all data including downloads"
	@echo "    help         - Show this help"

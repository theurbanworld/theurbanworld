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

.PHONY: all clean download extract convert-100m convert-1km boundaries radial export test-cities status lint test help

# Default target
all: export

# Python environment
PYTHON := uv run python
UV := uv

# Data directories
RAW_DIR := data/raw
INTERIM_DIR := data/interim
PROCESSED_DIR := data/processed

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
# EXTRACTION PHASE
# ============================================================================

$(INTERIM_DIR)/urban_centers.parquet: $(RAW_DIR)/.download_complete .venv
	$(PYTHON) -m src.s02_extract_urban_centers

extract: $(INTERIM_DIR)/urban_centers.parquet
	@echo "Urban centers extracted."

# ============================================================================
# H3 CONVERSION PHASE
# ============================================================================

# 100m raster to H3 (2020 only)
$(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet: $(RAW_DIR)/.download_complete $(INTERIM_DIR)/urban_centers.parquet .venv
	$(PYTHON) -m src.s03_raster_to_h3_100m

convert-100m: $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet
	@echo "100m H3 conversion complete."

# 1km raster to H3 (time series)
$(INTERIM_DIR)/h3_pop_1km/time_series.parquet: $(RAW_DIR)/.download_complete .venv
	$(PYTHON) -m src.s04_raster_to_h3_1km

convert-1km: $(INTERIM_DIR)/h3_pop_1km/time_series.parquet
	@echo "1km H3 conversion complete."

# Both conversions
convert: convert-100m convert-1km

# ============================================================================
# CITY ANALYSIS PHASE
# ============================================================================

# City boundary extraction
$(INTERIM_DIR)/city_boundaries/.complete: $(INTERIM_DIR)/urban_centers.parquet $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet .venv
	$(PYTHON) -m src.s05_extract_city_boundaries
	touch $@

boundaries: $(INTERIM_DIR)/city_boundaries/.complete
	@echo "City boundaries extracted."

# Radial density profiles
$(INTERIM_DIR)/radial_profiles/.complete: $(INTERIM_DIR)/urban_centers.parquet $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet .venv
	$(PYTHON) -m src.s06_compute_radial_profiles
	touch $@

radial: $(INTERIM_DIR)/radial_profiles/.complete
	@echo "Radial profiles computed."

# ============================================================================
# EXPORT PHASE
# ============================================================================

$(PROCESSED_DIR)/city_index.json: $(INTERIM_DIR)/urban_centers.parquet \
                                   $(INTERIM_DIR)/h3_pop_1km/time_series.parquet \
                                   $(INTERIM_DIR)/city_boundaries/.complete \
                                   $(INTERIM_DIR)/radial_profiles/.complete \
                                   .venv
	$(PYTHON) -m src.s07_export_web_formats

export: $(PROCESSED_DIR)/city_index.json
	@echo "Web export complete. Data ready in $(PROCESSED_DIR)/"

# ============================================================================
# TEST CITIES (Fast iteration)
# ============================================================================

test-cities: .venv
	@echo "Running pipeline for test cities only..."
	$(PYTHON) -m src.s01_download_ghsl --test-only
	$(PYTHON) -m src.s02_extract_urban_centers --test-only
	$(PYTHON) -m src.s03_raster_to_h3_100m --test-only
	$(PYTHON) -m src.s04_raster_to_h3_1km --test-only
	$(PYTHON) -m src.s05_extract_city_boundaries --test-only
	$(PYTHON) -m src.s06_compute_radial_profiles --test-only
	$(PYTHON) -m src.s07_export_web_formats --test-only
	@echo "Test cities pipeline complete."

# ============================================================================
# UTILITIES
# ============================================================================

# Show pipeline status
status:
	@echo "=== Pipeline Status ==="
	@echo "Download:   $$(test -f $(RAW_DIR)/.download_complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Extract:    $$(test -f $(INTERIM_DIR)/urban_centers.parquet && echo 'COMPLETE' || echo 'PENDING')"
	@echo "H3 100m:    $$(test -f $(PROCESSED_DIR)/h3_tiles/h3_pop_2020_res9.parquet && echo 'COMPLETE' || echo 'PENDING')"
	@echo "H3 1km:     $$(test -f $(INTERIM_DIR)/h3_pop_1km/time_series.parquet && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Boundaries: $$(test -f $(INTERIM_DIR)/city_boundaries/.complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Radial:     $$(test -f $(INTERIM_DIR)/radial_profiles/.complete && echo 'COMPLETE' || echo 'PENDING')"
	@echo "Export:     $$(test -f $(PROCESSED_DIR)/city_index.json && echo 'COMPLETE' || echo 'PENDING')"

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
	@echo "    extract      - Extract urban centers from UCDB"
	@echo "    convert-100m - Convert 100m raster to H3"
	@echo "    convert-1km  - Convert 1km raster to H3 (time series)"
	@echo "    boundaries   - Extract city boundary H3 cells"
	@echo "    radial       - Compute radial density profiles"
	@echo "    export       - Export web-ready JSON/GeoParquet"
	@echo ""
	@echo "  Shortcuts:"
	@echo "    all          - Run full pipeline (default)"
	@echo "    test-cities  - Run pipeline for 6 test cities only"
	@echo "    convert      - Run both H3 conversions"
	@echo ""
	@echo "  Utilities:"
	@echo "    status       - Show pipeline progress"
	@echo "    test         - Run pytest tests"
	@echo "    lint         - Run ruff linter"
	@echo "    format       - Format code with ruff"
	@echo "    clean        - Remove interim/processed data"
	@echo "    clean-all    - Remove all data including downloads"
	@echo "    help         - Show this help"

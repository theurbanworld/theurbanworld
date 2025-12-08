"""
Pipeline configuration and constants.

Purpose: Central configuration for all pipeline scripts
Decision log:
  - Using pydantic-settings for type-safe config with env var support
  - Paths are relative to project root for portability
  - H3 res 9 for maps (~0.1 km²), res 10 for radial profiles (~0.015 km²)
  - Population threshold of 100 per cell captures urban fringe
Date: 2024-12-08
"""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings


class PipelineConfig(BaseSettings):
    """Configuration loaded from environment or defaults."""

    # Paths (computed from project root)
    PROJECT_ROOT: ClassVar[Path] = Path(__file__).parent.parent.parent
    DATA_DIR: ClassVar[Path] = PROJECT_ROOT / "data"
    RAW_DIR: ClassVar[Path] = DATA_DIR / "raw"
    INTERIM_DIR: ClassVar[Path] = DATA_DIR / "interim"
    PROCESSED_DIR: ClassVar[Path] = DATA_DIR / "processed"

    # GHSL settings
    GHSL_BASE_URL: str = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL"
    GHSL_POP_RELEASE: str = "R2023A"
    GHSL_UCDB_RELEASE: str = "R2024A"
    GHSL_POP_EPOCHS: list[int] = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]
    GHSL_PROJECTION: int = 54009  # World Mollweide

    # H3 settings
    H3_RESOLUTION_MAP: int = 9  # ~0.105 km² per cell - for map tiles
    H3_RESOLUTION_RADIAL: int = 10  # ~0.015 km² per cell - for radial profiles

    # Radial profile settings (Bertaud methodology)
    RADIAL_MAX_DISTANCE_KM: float = 50.0
    RADIAL_RING_WIDTH_KM: float = 1.0
    RADIAL_NUM_RINGS: int = 50

    # City boundary settings
    BOUNDARY_POPULATION_THRESHOLD: int = 100  # Min population per H3 cell to include
    BOUNDARY_MIN_CELLS: int = 10  # Min cells for valid city boundary

    # Processing settings
    RASTER_CHUNK_SIZE: tuple[int, int] = (2048, 2048)
    CITY_BATCH_SIZE: int = 100
    PARALLEL_WORKERS: int = 8

    # Download settings
    DOWNLOAD_TIMEOUT: int = 600  # seconds
    DOWNLOAD_RETRIES: int = 3
    DOWNLOAD_BACKOFF_FACTOR: float = 2.0

    # Memory settings for Apple Silicon
    DASK_MEMORY_LIMIT: str = "12GB"
    DASK_THREADS_PER_WORKER: int = 8

    # Test cities for development
    TEST_CITIES: list[str] = [
        "New York",
        "Paris",
        "Singapore",
        "Lagos",
        "Rio de Janeiro",
        "Geneva",
    ]

    class Config:
        env_prefix = "URBAN_"
        case_sensitive = False


# Global config instance
config = PipelineConfig()


# Convenience path accessors
def get_raw_path(subdir: str = "") -> Path:
    """Get path in raw data directory."""
    path = config.RAW_DIR / subdir if subdir else config.RAW_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_interim_path(subdir: str = "") -> Path:
    """Get path in interim data directory."""
    path = config.INTERIM_DIR / subdir if subdir else config.INTERIM_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_processed_path(subdir: str = "") -> Path:
    """Get path in processed data directory."""
    path = config.PROCESSED_DIR / subdir if subdir else config.PROCESSED_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


# GHSL URL builders
def get_ghsl_pop_tile_url(epoch: int, resolution: int, row: int, col: int) -> str:
    """
    Build GHSL-POP tile download URL.

    Example output:
    https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/
    GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0/V1-0/tiles/
    GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R5_C19.zip
    """
    release = config.GHSL_POP_RELEASE
    proj = config.GHSL_PROJECTION
    res_str = str(resolution)

    product_dir = f"GHS_POP_GLOBE_{release}"
    file_base = f"GHS_POP_E{epoch}_GLOBE_{release}_{proj}_{res_str}_V1_0"
    tile_id = f"R{row}_C{col}"

    return f"{config.GHSL_BASE_URL}/{product_dir}/{file_base}/V1-0/tiles/{file_base}_{tile_id}.zip"


def get_ghsl_pop_global_url(epoch: int, resolution: int) -> str:
    """
    Build GHSL-POP global file download URL (for 1km data).

    The 1km data comes as a single global file, not tiles.
    """
    release = config.GHSL_POP_RELEASE
    proj = config.GHSL_PROJECTION
    res_str = str(resolution)

    product_dir = f"GHS_POP_GLOBE_{release}"
    file_base = f"GHS_POP_E{epoch}_GLOBE_{release}_{proj}_{res_str}_V1_0"

    return f"{config.GHSL_BASE_URL}/{product_dir}/{file_base}/V1-0/{file_base}.zip"


def get_ghsl_ucdb_url() -> str:
    """Build GHSL-UCDB download URL."""
    release = config.GHSL_UCDB_RELEASE
    return (
        f"{config.GHSL_BASE_URL}/GHS_STAT_UCDB2015MT_GLOBE_{release}/"
        f"GHS_STAT_UCDB2015MT_GLOBE_{release}_V1_0.zip"
    )

"""
Extract UCDB data from GeoPackage and XLSX.

Purpose: Parse GHSL-UCDB to extract all thematic data for querying

Input:
  - data/raw/ucdb/GHS_UCDB_GLOBE_R2024A.gpkg (16 layers)
  - data/raw/ucdb/GHS_UCDB_GLOBE_R2024A.xlsx (Index sheet for schema)
Output:
  - data/raw/ucdb/ucdb_schema.json (human-readable column definitions)
  - data/interim/ucdb/themes/*.parquet (15 thematic tables)
  - data/interim/ucdb/ucdb_all.parquet (merged wide table)

Decision log:
  - All thematic layers share ID_UC_G0 as join key
  - Extract schema from XLSX Index for human-readable column names
  - Store geometry separately to keep thematic tables lightweight
  - Column names have BOM prefix in GPKG that needs cleaning
Date: 2025-12-09
"""

import json
from pathlib import Path

import click
import geopandas as gpd
import pandas as pd
import polars as pl

from .utils.config import config, get_interim_path, get_raw_path


# GeoPackage layer names
GPKG_LAYER_NAMES = {
    "GENERAL_CHARACTERISTICS": "GHS_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A",
    "GHSL": "GHS_UCDB_THEME_GHSL_GLOBE_R2024A",
    "CLIMATE": "GHS_UCDB_THEME_CLIMATE_GLOBE_R2024A",
    "EMISSIONS": "GHS_UCDB_THEME_EMISSIONS_GLOBE_R2024A",
    "EXPOSURE": "GHS_UCDB_THEME_EXPOSURE_GLOBE_R2024A",
    "GEOGRAPHY": "GHS_UCDB_THEME_GEOGRAPHY_GLOBE_R2024A",
    "GREENNESS": "GHS_UCDB_THEME_GREENNESS_GLOBE_R2024A",
    "HAZARD_RISK": "GHS_UCDB_THEME_HAZARD_RISK_GLOBE_R2024A",
    "HEALTH": "GHS_UCDB_THEME_HEALTH_GLOBE_R2024A",
    "INFRASTRUCTURES": "GHS_UCDB_THEME_INFRASTRUCTURES_GLOBE_R2024A",
    "LULC": "GHS_UCDB_THEME_LULC_GLOBE_R2024A",
    "NATURAL_SYSTEMS": "GHS_UCDB_THEME_NATURAL_SYSTEMS_GLOBE_R2024A",
    "SDG": "GHS_UCDB_THEME_SDG_GLOBE_R2024A",
    "SOCIOECONOMIC": "GHS_UCDB_THEME_SOCIOECONOMIC_GLOBE_R2024A",
    "WATER": "GHS_UCDB_THEME_WATER_GLOBE_R2024A",
}

# Mapping from Index "Thematic Area" to layer key
THEMATIC_AREA_TO_LAYER = {
    "General Characteristics": "GENERAL_CHARACTERISTICS",
    "GHSL": "GHSL",
    "Climate": "CLIMATE",
    "Emissions": "EMISSIONS",
    "Exposure": "EXPOSURE",
    "Geography": "GEOGRAPHY",
    "Greenness": "GREENNESS",
    "Hazard_Risk": "HAZARD_RISK",
    "Health": "HEALTH",
    "Infrastructures": "INFRASTRUCTURES",
    "LULC": "LULC",
    "Natural_Systems": "NATURAL_SYSTEMS",
    "SDG": "SDG",
    "Socioeconomic": "SOCIOECONOMIC",
    "Water": "WATER",
}

# Common columns present in all thematic layers (for deduplication)
COMMON_COLUMNS = {
    "ID_UC_G0",
    "GC_UCN_MAI_2025",
    "GC_CNT_GAD_2025",
    "GC_UCA_KM2_2025",
    "GC_POP_TOT_2025",
}


def clean_column_name(col: str) -> str:
    """Remove BOM character and normalize column names."""
    return col.lstrip("\ufeff").strip()


def clean_string_values(df: pl.DataFrame) -> pl.DataFrame:
    """Remove BOM character from all string column values."""
    for col in df.columns:
        if df[col].dtype == pl.Utf8:
            df = df.with_columns(pl.col(col).str.strip_chars("\ufeff").alias(col))
    return df


# =============================================================================
# SCHEMA EXTRACTION (from XLSX Index)
# =============================================================================


def load_index_sheet(xlsx_path: Path) -> pd.DataFrame:
    """Load and clean the Index sheet from UCDB XLSX."""
    print(f"Loading Index sheet from {xlsx_path}...")
    df = pd.read_excel(xlsx_path, sheet_name="Index", engine="openpyxl")

    # Filter to rows with Attribute ID
    df = df[df["Attribute ID"].notna()].copy()
    print(f"  Found {len(df)} attribute definitions")

    # Forward-fill Thematic Area and Group
    df["Thematic Area"] = df["Thematic Area"].ffill()
    df["Group"] = df["Group"].ffill()

    return df


def extract_schema(df: pd.DataFrame) -> dict:
    """Extract schema dictionary from Index dataframe."""
    schema = {
        "version": "R2024A",
        "description": "UCDB column schema extracted from XLSX Index sheet",
        "columns": {},
    }

    for _, row in df.iterrows():
        attr_id = str(row["Attribute ID"]).strip()

        # Clean up indicator name
        indicator = row.get("Indicator Name")
        if pd.isna(indicator):
            indicator = row.get("Group", "")

        # Clean up unit
        unit = row.get("Unit")
        if pd.isna(unit) or unit == "-":
            unit = None
        else:
            unit = str(unit).strip()

        # Map thematic area to layer
        thematic_area = row.get("Thematic Area", "")
        layer = None
        if thematic_area:
            for key, value in THEMATIC_AREA_TO_LAYER.items():
                if key.lower() in str(thematic_area).lower():
                    layer = value
                    break

        # Extract source and methodology
        source = row.get("Source")
        if pd.isna(source):
            source = None
        else:
            source = str(source).strip()

        methodology = row.get("Methodology")
        if pd.isna(methodology):
            methodology = None
        else:
            methodology = str(methodology).strip()

        schema["columns"][attr_id] = {
            "description": str(indicator).strip() if indicator else None,
            "thematic_area": str(thematic_area).strip() if thematic_area else None,
            "group": str(row.get("Group", "")).strip() or None,
            "unit": unit,
            "layer": layer,
            "source": source,
            "methodology": methodology,
        }

    return schema


def create_column_aliases(schema: dict) -> dict:
    """Create mapping from common names to actual column patterns."""
    aliases = {
        "name": ["GC_UCN_MAI_XXXX", "UC_NM_MN"],
        "country_code": ["GC_CNT_GAD_XXXX", "CTR_MN_ISO", "GC_CNT_UNN_XXXX"],
        "population": ["GC_POP_TOT_XXXX", "P20", "P15"],
        "area_km2": ["GC_UCA_KM2_XXXX", "AREA"],
        "city_id": ["ID_UC_G0", "ID_HDC_G0"],
    }
    schema["aliases"] = aliases
    return schema


def add_layer_info(schema: dict, gpkg_path: Path) -> dict:
    """Add layer information to schema by inspecting the GeoPackage."""
    schema["layers"] = {}

    for layer_key, layer_name in GPKG_LAYER_NAMES.items():
        try:
            # Read just the column names (no data)
            gdf = gpd.read_file(gpkg_path, layer=layer_name, rows=1)
            columns = [clean_column_name(c) for c in gdf.columns if c != "geometry"]

            schema["layers"][layer_key] = {
                "gpkg_name": layer_name,
                "parquet_file": f"themes/{layer_key.lower()}.parquet",
                "column_count": len(columns),
            }
        except Exception as e:
            print(f"  Warning: Could not read layer {layer_name}: {e}")

    return schema


# =============================================================================
# THEME EXTRACTION (from GeoPackage)
# =============================================================================


def extract_theme_to_parquet(
    gpkg_path: Path,
    theme: str,
    output_path: Path,
    exclude_common: bool = True,
) -> pl.DataFrame:
    """
    Extract a single thematic layer to Parquet (without geometry).

    Args:
        gpkg_path: Path to GeoPackage
        theme: Theme key (e.g., "CLIMATE")
        output_path: Output parquet path
        exclude_common: If True, exclude common columns except ID_UC_G0

    Returns:
        Polars DataFrame of the extracted data
    """
    layer_name = GPKG_LAYER_NAMES[theme]
    print(f"  Extracting {theme} from {layer_name}...")

    gdf = gpd.read_file(gpkg_path, layer=layer_name)

    # Clean column names
    gdf.columns = [clean_column_name(c) for c in gdf.columns]

    # Drop geometry
    df = pd.DataFrame(gdf.drop(columns=["geometry"]))

    # Exclude common columns (except ID_UC_G0) unless this is GENERAL_CHARACTERISTICS
    if exclude_common and theme != "GENERAL_CHARACTERISTICS":
        cols_to_keep = [c for c in df.columns if c == "ID_UC_G0" or c not in COMMON_COLUMNS]
        df = df[cols_to_keep]

    # Convert to Polars
    pl_df = pl.from_pandas(df)

    # Clean BOM from string values
    pl_df = clean_string_values(pl_df)

    # Write parquet
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pl_df.write_parquet(output_path)

    print(f"    -> {len(pl_df)} rows, {len(pl_df.columns)} columns")
    return pl_df


def extract_all_themes(
    gpkg_path: Path,
    output_dir: Path,
    themes: list[str] | None = None,
) -> dict[str, pl.DataFrame]:
    """
    Extract all thematic layers to parquet files.

    Args:
        gpkg_path: Path to GeoPackage
        output_dir: Base output directory (will create themes/ subdir)
        themes: List of themes to extract, or None for all

    Returns:
        Dict mapping theme name to DataFrame
    """
    themes_dir = output_dir / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)

    if themes is None:
        themes = list(GPKG_LAYER_NAMES.keys())

    results = {}
    for theme in themes:
        if theme not in GPKG_LAYER_NAMES:
            print(f"  Warning: Unknown theme '{theme}', skipping")
            continue

        output_path = themes_dir / f"{theme.lower()}.parquet"
        results[theme] = extract_theme_to_parquet(
            gpkg_path, theme, output_path, exclude_common=True
        )

    return results


def merge_all_themes(themes_dir: Path, output_path: Path) -> pl.DataFrame:
    """
    Merge all theme Parquets into single wide file joined on ID_UC_G0.

    Args:
        themes_dir: Directory containing theme parquet files
        output_path: Output path for merged parquet

    Returns:
        Merged Polars DataFrame
    """
    print("Merging all themes into single wide table...")

    # Start with GENERAL_CHARACTERISTICS as base (has all common columns)
    base_path = themes_dir / "general_characteristics.parquet"
    if not base_path.exists():
        raise FileNotFoundError(f"Base file not found: {base_path}")

    merged = pl.read_parquet(base_path)
    existing_cols = set(merged.columns)
    print(f"  Base: {len(merged.columns)} columns from general_characteristics")

    # Join other themes
    for parquet_file in sorted(themes_dir.glob("*.parquet")):
        if parquet_file.name == "general_characteristics.parquet":
            continue

        df = pl.read_parquet(parquet_file)

        # Only keep columns that aren't already in merged (except ID_UC_G0)
        new_cols = [c for c in df.columns if c == "ID_UC_G0" or c not in existing_cols]
        if len(new_cols) <= 1:  # Only ID_UC_G0
            print(f"  Skipped {parquet_file.stem} (no new columns)")
            continue

        df = df.select(new_cols)
        merged = merged.join(df, on="ID_UC_G0", how="left")
        existing_cols.update(new_cols)
        print(f"  Added {len(new_cols) - 1} columns from {parquet_file.stem}")

    print(f"  Total: {len(merged.columns)} columns")
    merged.write_parquet(output_path)
    return merged


# =============================================================================
# CLI
# =============================================================================


@click.group()
def cli():
    """UCDB extraction commands."""
    pass


@cli.command()
def schema():
    """Extract schema from XLSX Index sheet."""
    print("=" * 60)
    print("UCDB Schema Extraction")
    print("=" * 60)

    ucdb_dir = get_raw_path("ucdb")
    xlsx_files = list(ucdb_dir.glob("*.xlsx"))
    gpkg_files = list(ucdb_dir.glob("*.gpkg"))

    if not xlsx_files:
        print("ERROR: No XLSX file found in UCDB directory.")
        return

    xlsx_path = xlsx_files[0]
    print(f"Using XLSX: {xlsx_path.name}")

    # Load and parse Index sheet
    df = load_index_sheet(xlsx_path)

    # Extract schema
    print("\nExtracting schema...")
    schema = extract_schema(df)
    schema = create_column_aliases(schema)

    # Add layer info if GPKG available
    if gpkg_files:
        print("\nInspecting GeoPackage layers...")
        schema = add_layer_info(schema, gpkg_files[0])

    # Save schema
    output_path = ucdb_dir / "ucdb_schema.json"
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"\nSaved schema to {output_path}")
    print(f"  Total columns defined: {len(schema['columns'])}")

    # Print summary
    print("\nColumns by thematic area:")
    areas = {}
    for col_id, col_info in schema["columns"].items():
        area = col_info.get("thematic_area") or "Unknown"
        areas[area] = areas.get(area, 0) + 1

    for area, count in sorted(areas.items()):
        print(f"  {area}: {count}")


@cli.command()
@click.option("--themes", default=None, help="Comma-separated themes to extract (default: all)")
def extract(themes: str | None):
    """Extract all thematic data."""
    print("=" * 60)
    print("UCDB Data Extraction")
    print("=" * 60)

    ucdb_dir = get_raw_path("ucdb")
    gpkg_files = list(ucdb_dir.glob("*.gpkg"))

    if not gpkg_files:
        print("ERROR: No GeoPackage found. Run download first.")
        return

    gpkg_path = gpkg_files[0]
    output_dir = get_interim_path("ucdb")

    # Parse themes if specified
    themes_list = None
    if themes:
        themes_list = [t.strip().upper() for t in themes.split(",")]
        print(f"Extracting themes: {themes_list}")

    # Extract all themes
    print("\n--- Extracting Thematic Layers ---")
    extract_all_themes(gpkg_path, output_dir, themes_list)

    # Merge into single wide table
    print("\n--- Merging Themes ---")
    merge_all_themes(output_dir / "themes", output_dir / "ucdb_all.parquet")

    # Create sentinel file
    sentinel = output_dir / ".extract_complete"
    sentinel.touch()

    # Summary
    print("\n" + "=" * 60)
    print("Extraction Complete")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print(f"Themes extracted: {len(list((output_dir / 'themes').glob('*.parquet')))}")
    print("Note: Run s02b_extract_cities for city metadata")


@cli.command(name="all")
def run_all():
    """Run full extraction (schema + data)."""
    print("=" * 60)
    print("UCDB Full Extraction")
    print("=" * 60)

    # Run schema extraction
    ctx = click.Context(schema)
    ctx.invoke(schema)

    print("\n")

    # Run data extraction
    ctx = click.Context(extract)
    ctx.invoke(extract, themes=None)


if __name__ == "__main__":
    cli()

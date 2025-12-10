"""
02a - UCDB Data Explorer (Streamlit).

Purpose: Interactive web interface to explore UCDB data
Input:
  - data/interim/urban_centers.parquet (city list)
  - data/interim/ucdb/ucdb_all.parquet (full attributes)
  - data/raw/ucdb/ucdb_schema.json (column definitions)
Output: Web interface (no files created)

Usage:
  uv run streamlit run src/s02a_explore_ucdb.py

Date: 2024-12-10
"""

import json
from pathlib import Path

import pandas as pd
import polars as pl
import streamlit as st

# Resolve paths relative to this file
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"


# =============================================================================
# DATA LOADING (cached)
# =============================================================================


@st.cache_data
def load_urban_centers() -> pd.DataFrame:
    """Load urban centers metadata."""
    path = INTERIM_DIR / "urban_centers.parquet"
    if not path.exists():
        st.error(f"File not found: {path}\n\nRun `make extract-ucdb` first.")
        st.stop()
    return pl.read_parquet(path).to_pandas()


@st.cache_data
def load_ucdb_all() -> pd.DataFrame:
    """Load full UCDB attributes (500+ columns)."""
    path = INTERIM_DIR / "ucdb" / "ucdb_all.parquet"
    if not path.exists():
        st.error(f"File not found: {path}\n\nRun `make extract-ucdb` first.")
        st.stop()
    return pl.read_parquet(path).to_pandas()


@st.cache_data
def load_schema() -> dict:
    """Load UCDB schema with column definitions."""
    path = RAW_DIR / "ucdb" / "ucdb_schema.json"
    if not path.exists():
        st.warning(f"Schema not found: {path}")
        return {"columns": {}, "layers": {}}
    with open(path) as f:
        return json.load(f)


# =============================================================================
# UI COMPONENTS
# =============================================================================


def render_city_browser():
    """Render searchable city table."""
    st.header("City Browser")

    df = load_urban_centers()

    # Search box
    search = st.text_input("Search cities", placeholder="e.g., New York, Paris, Tokyo...")

    # Filter by search
    if search:
        mask = df["name"].str.contains(search, case=False, na=False)
        df = df[mask]

    # Display stats
    st.caption(f"Showing {len(df):,} of {len(load_urban_centers()):,} cities")

    # Population filter
    col1, col2 = st.columns(2)
    with col1:
        min_pop = st.number_input("Min population", value=0, step=100000)
    with col2:
        max_pop = st.number_input("Max population", value=50_000_000, step=100000)

    df = df[(df["population_2020"] >= min_pop) & (df["population_2020"] <= max_pop)]

    # Select columns to display
    display_cols = ["name", "country_code", "population_2020", "area_km2", "latitude", "longitude"]
    display_df = df[display_cols].copy()
    display_df.columns = ["Name", "Country", "Population (2020)", "Area (km²)", "Latitude", "Longitude"]

    # Sort by population by default
    display_df = display_df.sort_values("Population (2020)", ascending=False)

    # Show table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Population (2020)": st.column_config.NumberColumn(format="%d"),
            "Area (km²)": st.column_config.NumberColumn(format="%.1f"),
            "Latitude": st.column_config.NumberColumn(format="%.4f"),
            "Longitude": st.column_config.NumberColumn(format="%.4f"),
        },
    )

    # City detail selector
    st.divider()
    st.subheader("City Details")

    city_names = df["name"].tolist()
    if city_names:
        selected_city = st.selectbox("Select a city to view details", city_names)
        if selected_city:
            render_city_detail(selected_city)


def render_city_detail(city_name: str):
    """Render detailed view for a single city."""
    urban_centers = load_urban_centers()
    ucdb_all = load_ucdb_all()
    schema = load_schema()

    # Find city
    city_row = urban_centers[urban_centers["name"] == city_name].iloc[0]
    city_id = city_row["city_id"]

    # Get full attributes
    ucdb_row = ucdb_all[ucdb_all["ID_UC_G0"] == int(city_id)]
    if ucdb_row.empty:
        st.warning(f"No UCDB data found for city_id: {city_id}")
        return

    ucdb_row = ucdb_row.iloc[0]

    # Basic info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Population (2020)", f"{city_row['population_2020']:,.0f}")
    with col2:
        st.metric("Area", f"{city_row['area_km2']:.1f} km²")
    with col3:
        st.metric("Country", city_row["country_code"])

    # Group attributes by thematic area
    st.subheader("All Attributes")

    columns_info = schema.get("columns", {})

    # Build attribute table
    attrs = []
    for col_name, value in ucdb_row.items():
        if col_name == "ID_UC_G0":
            continue

        col_info = columns_info.get(col_name, {})
        description = col_info.get("description", col_name)
        thematic_area = col_info.get("thematic_area", "Other")
        unit = col_info.get("unit", "")

        # Format value
        if pd.isna(value):
            formatted_value = "—"
        elif isinstance(value, float):
            formatted_value = f"{value:,.2f}"
        else:
            formatted_value = str(value)

        if unit:
            formatted_value = f"{formatted_value} {unit}"

        attrs.append({
            "Column": col_name,
            "Description": description,
            "Value": formatted_value,
            "Theme": thematic_area or "Other",
        })

    attrs_df = pd.DataFrame(attrs)

    # Filter by theme
    themes = sorted(attrs_df["Theme"].unique())
    selected_theme = st.selectbox("Filter by thematic area", ["All"] + themes)

    if selected_theme != "All":
        attrs_df = attrs_df[attrs_df["Theme"] == selected_theme]

    st.dataframe(attrs_df, use_container_width=True, hide_index=True)


def render_schema_explorer():
    """Render schema browser."""
    st.header("Schema Explorer")

    schema = load_schema()
    columns_info = schema.get("columns", {})

    if not columns_info:
        st.warning("No schema loaded. Run `uv run python -m src.s02_extract_ucdb schema` first.")
        return

    st.caption(f"{len(columns_info)} column definitions")

    # Build schema table
    schema_data = []
    for col_id, col_info in columns_info.items():
        schema_data.append({
            "Column ID": col_id,
            "Description": col_info.get("description", ""),
            "Theme": col_info.get("thematic_area", ""),
            "Group": col_info.get("group", ""),
            "Unit": col_info.get("unit", ""),
            "Source": col_info.get("source", ""),
        })

    schema_df = pd.DataFrame(schema_data)

    # Filter by theme
    themes = sorted(schema_df["Theme"].dropna().unique())
    selected_theme = st.selectbox("Filter by thematic area", ["All"] + list(themes))

    if selected_theme != "All":
        schema_df = schema_df[schema_df["Theme"] == selected_theme]

    # Search
    search = st.text_input("Search columns", placeholder="e.g., population, emissions, climate...")
    if search:
        mask = (
            schema_df["Column ID"].str.contains(search, case=False, na=False) |
            schema_df["Description"].str.contains(search, case=False, na=False)
        )
        schema_df = mask_df = schema_df[mask]

    st.dataframe(schema_df, use_container_width=True, hide_index=True)

    # Layer info
    st.divider()
    st.subheader("Thematic Layers")

    layers = schema.get("layers", {})
    if layers:
        layer_data = []
        for layer_key, layer_info in layers.items():
            layer_data.append({
                "Layer": layer_key,
                "GeoPackage Name": layer_info.get("gpkg_name", ""),
                "Parquet File": layer_info.get("parquet_file", ""),
                "Columns": layer_info.get("column_count", 0),
            })
        st.dataframe(pd.DataFrame(layer_data), use_container_width=True, hide_index=True)


def render_map():
    """Render city map."""
    st.header("City Map")

    df = load_urban_centers()

    # Population filter
    min_pop = st.slider(
        "Minimum population",
        min_value=0,
        max_value=10_000_000,
        value=500_000,
        step=100_000,
    )

    filtered_df = df[df["population_2020"] >= min_pop]
    st.caption(f"Showing {len(filtered_df):,} cities with population >= {min_pop:,}")

    # Prepare map data
    map_df = filtered_df[["latitude", "longitude", "name", "population_2020"]].copy()
    map_df = map_df.rename(columns={"latitude": "lat", "longitude": "lon"})

    st.map(map_df, size="population_2020", color="#0068c9")


# =============================================================================
# MAIN
# =============================================================================


def main():
    st.set_page_config(
        page_title="UCDB Explorer",
        page_icon="🌍",
        layout="wide",
    )

    st.title("UCDB Explorer")
    st.caption("Explore the Global Human Settlement Layer Urban Centre Database (GHSL-UCDB R2024A)")

    # Navigation
    page = st.sidebar.radio(
        "View",
        ["Cities", "Schema", "Map"],
        captions=["Browse 11,422 cities", "500+ column definitions", "World map"],
    )

    if page == "Cities":
        render_city_browser()
    elif page == "Schema":
        render_schema_explorer()
    elif page == "Map":
        render_map()


if __name__ == "__main__":
    main()

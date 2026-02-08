"""
City Data Explorer - Streamlit app for browsing city data and validation results.

Usage:
    uv run streamlit run src/app_explore.py

Features:
    - Summary tab: Row counts, validation status, quick stats
    - Cities tab: Searchable/filterable city browser
    - Outliers tab: View statistical anomalies from validation
"""

import json
from pathlib import Path

import duckdb
import streamlit as st

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "processed" / "cities"
VALIDATION_REPORT = DATA_DIR / "validation_report.json"


@st.cache_data
def load_table(filename: str):
    """Load a parquet file using DuckDB."""
    path = DATA_DIR / filename
    if not path.exists():
        return None
    return duckdb.query(f"SELECT * FROM '{path}'").df()


@st.cache_data
def load_validation_report():
    """Load the most recent validation report JSON."""
    if not VALIDATION_REPORT.exists():
        return None
    return json.loads(VALIDATION_REPORT.read_text())


def render_summary():
    """Render the Summary tab."""
    st.header("Data Summary")

    # Load tables and show row counts
    tables = {
        "cities.parquet": "City metadata",
        "city_populations.parquet": "Population time series",
        "city_rankings.parquet": "Rankings per epoch",
        "city_growth.parquet": "Growth metrics (1975-2030)",
        "city_density_peers.parquet": "Density peer relationships",
    }

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Table Row Counts")
        for filename, description in tables.items():
            df = load_table(filename)
            if df is not None:
                st.metric(filename, f"{len(df):,} rows")
            else:
                st.metric(filename, "Not found", delta="missing")

    with col2:
        st.subheader("Quick Stats")
        cities = load_table("cities.parquet")
        if cities is not None:
            st.metric("Countries", cities["country_code"].nunique())
            st.metric("Regions", cities["region"].nunique())

            # Top population
            pop = load_table("city_populations.parquet")
            if pop is not None:
                pop_2025 = pop[pop["epoch"] == 2025]
                total_pop = pop_2025["population"].sum()
                st.metric("Total Urban Pop (2025)", f"{total_pop/1e9:.2f}B")

    # Validation status
    st.subheader("Validation Status")
    report = load_validation_report()
    if report:
        cols = st.columns(4)
        cols[0].metric("Errors", report["summary"]["total_errors"])
        cols[1].metric("Warnings", report["summary"]["total_warnings"])
        cols[2].metric("Outliers", report["summary"].get("total_outliers", "N/A"))
        cols[3].metric("Passed", "Yes" if report["summary"]["passed"] else "No")
        st.caption(f"Report timestamp: {report['timestamp']}")
    else:
        st.info("No validation report found. Run: `uv run python -m src.s99_validate_cities -o data/processed/cities/validation_report.json`")


def render_cities():
    """Render the Cities browser tab."""
    st.header("City Browser")

    cities = load_table("cities.parquet")
    if cities is None:
        st.error("cities.parquet not found")
        return

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        countries = ["All"] + sorted(cities["country_code"].dropna().unique().tolist())
        selected_country = st.selectbox("Country", countries)

    with col2:
        regions = ["All"] + sorted(cities["region"].dropna().unique().tolist())
        selected_region = st.selectbox("Region", regions)

    with col3:
        search = st.text_input("Search by name")

    # Apply filters
    filtered = cities.copy()
    if selected_country != "All":
        filtered = filtered[filtered["country_code"] == selected_country]
    if selected_region != "All":
        filtered = filtered[filtered["region"] == selected_region]
    if search:
        filtered = filtered[filtered["name"].str.contains(search, case=False, na=False)]

    # Display columns
    display_cols = [
        "city_id", "name", "country_code", "region",
        "ucdb_population_2025", "ucdb_area_km2_2025"
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.write(f"Showing {len(filtered):,} of {len(cities):,} cities")
    st.dataframe(
        filtered[display_cols].sort_values("ucdb_population_2025", ascending=False),
        use_container_width=True,
        height=500,
    )


def render_outliers():
    """Render the Outliers tab."""
    st.header("Statistical Outliers")

    report = load_validation_report()
    if not report:
        st.info("No validation report found. Run: `uv run python -m src.s99_validate_cities -o data/processed/cities/validation_report.json`")
        return

    statistical_checks = report.get("statistical_checks", {})
    if not statistical_checks:
        st.success("No outliers detected!")
        return

    # Summary metrics
    cols = st.columns(len(statistical_checks))
    for i, (check_name, items) in enumerate(statistical_checks.items()):
        cols[i].metric(check_name.replace("_", " ").title(), len(items))

    st.divider()

    # Detailed view per check type
    check_names = list(statistical_checks.keys())
    selected_check = st.selectbox("Select outlier type", check_names)

    if selected_check:
        items = statistical_checks[selected_check]
        st.write(f"**{len(items)} outliers found**")

        # Convert to dataframe for display
        import pandas as pd
        df = pd.DataFrame(items)
        st.dataframe(df, use_container_width=True, height=400)


def main():
    st.set_page_config(
        page_title="City Data Explorer",
        page_icon="🏙️",
        layout="wide",
    )

    st.title("🏙️ City Data Explorer")

    tab1, tab2, tab3 = st.tabs(["Summary", "Cities", "Outliers"])

    with tab1:
        render_summary()

    with tab2:
        render_cities()

    with tab3:
        render_outliers()


if __name__ == "__main__":
    main()

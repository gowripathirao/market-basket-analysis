import ast
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

PROJECT_DIR = Path(__file__).resolve().parent

DEFAULT_FILES = [
    "traditional_rules_apriori.csv",
    "traditional_rules_fp_growth.csv",
    "contextual_rules_apriori.csv",
    "contextual_rules_fp_growth.csv",
]


def _parse_frozenset_cell(value: str) -> str:
    if not isinstance(value, str):
        return str(value)
    v = value.strip()
    if not v.startswith("frozenset("):
        return v
    try:
        inside = v[len("frozenset("): -1]
        items = ast.literal_eval(inside)
        if isinstance(items, (set, frozenset, list, tuple)):
            return ", ".join(sorted(map(str, items)))
        return str(items)
    except Exception:
        return v


@st.cache_data(show_spinner=False)
def load_rules_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ("antecedents", "consequents"):
        if col in df.columns:
            df[col] = df[col].map(_parse_frozenset_cell)
    return df


def main():
    st.set_page_config(page_title="Market Basket Outputs", layout="wide")
    st.title("Market Basket Analysis Outputs")
    st.caption("Advanced filtering + visualization + country insights")

    available_files = [f for f in DEFAULT_FILES if (PROJECT_DIR / f).exists()]
    extra_csvs = sorted([p.name for p in PROJECT_DIR.glob("*.csv") if p.name not in set(DEFAULT_FILES)])
    file_options = available_files + extra_csvs

    if not file_options:
        st.error("No CSV outputs found.")
        return

    # ================= SIDEBAR =================
    with st.sidebar:
        st.header("Load")
        selected = st.selectbox("CSV file", file_options)
        st.divider()
        st.header("Filters")

    df = load_rules_csv(str(PROJECT_DIR / selected))

    numeric_cols = [c for c in ["support", "confidence", "lift"] if c in df.columns]

    filters = {}
    with st.sidebar:
        for col in numeric_cols:
            series = pd.to_numeric(df[col], errors="coerce")
            lo = float(series.min())
            hi = float(series.max())
            filters[col] = st.slider(col, lo, hi, (lo, hi))

        text_query = st.text_input("Search rules", "")

        sort_col = st.selectbox("Sort by", numeric_cols)
        sort_desc = st.checkbox("Descending", True)
        max_rows = st.number_input("Max rows", 50, 20000, 2000)

    # ================= FILTERING =================
    filtered = df.copy()

    for col, (lo, hi) in filters.items():
        s = pd.to_numeric(filtered[col], errors="coerce")
        filtered = filtered[s.between(lo, hi)]

    if text_query:
        filtered = filtered[
            filtered["antecedents"].str.contains(text_query, case=False, na=False) |
            filtered["consequents"].str.contains(text_query, case=False, na=False)
        ]

    filtered = filtered.sort_values(by=sort_col, ascending=not sort_desc)

    # ================= TABLE =================
    st.subheader("Preview")
    st.dataframe(filtered.head(int(max_rows)), use_container_width=True)

    # ================= VISUALIZATIONS =================
    st.subheader("Visualizations")

    plot_df = filtered if len(filtered) < 5000 else filtered.sample(5000)

    for col in numeric_cols:
        fig = px.histogram(plot_df, x=col, title=f"{col} distribution")
        st.plotly_chart(fig, use_container_width=True)

    if {"support", "confidence"}.issubset(plot_df.columns):
        fig = px.scatter(plot_df, x="support", y="confidence", color="lift")
        st.plotly_chart(fig, use_container_width=True)

    top_rules = plot_df.nlargest(15, "lift")
    top_rules["rule"] = top_rules["antecedents"] + " → " + top_rules["consequents"]

    fig = px.bar(top_rules, x="lift", y="rule", orientation="h", title="Top Rules by Lift")
    st.plotly_chart(fig, use_container_width=True)

    # ================= COUNTRY-WISE =================
    st.subheader("🌍 Transactions by Country")

    df_country = pd.read_excel(PROJECT_DIR / "online_retail_II.xlsx")
    df_country = df_country.dropna(subset=['Description', 'Country'])
    df_country = df_country[df_country['Quantity'] > 0]

    country_counts = df_country['Country'].value_counts().reset_index()
    country_counts.columns = ['Country', 'Transactions']

    fig = px.bar(country_counts.head(10), x="Country", y="Transactions",
                 title="Top Countries by Transactions")
    st.plotly_chart(fig, use_container_width=True)

    # ================= TOP PRODUCTS =================
    st.subheader("🛒 Top Products by Country")

    country = st.selectbox("Select Country", df_country["Country"].unique())
    country_df = df_country[df_country["Country"] == country]

    top_products = country_df["Description"].value_counts().head(10).reset_index()
    top_products.columns = ["Product", "Count"]

    fig = px.bar(top_products, x="Product", y="Count",
                 title=f"Top Products in {country}")
    st.plotly_chart(fig, use_container_width=True)

    # ================= DOWNLOAD =================
    st.subheader("Download")

    st.download_button(
        "Download Filtered CSV",
        filtered.to_csv(index=False),
        "filtered_rules.csv"
    )


if __name__ == "__main__":
    main()
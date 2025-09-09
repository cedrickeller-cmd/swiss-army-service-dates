# app.py
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "service_dates.db"

# Helper to load data from DB
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM activeServiceDates", conn)
    conn.close()
    return df

# App layout
st.set_page_config(page_title="Swiss Army Service Dates", layout="wide")
st.title("Swiss Army Service Dates Lookup")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

languages = st.sidebar.multiselect(
    "Language",
    options=sorted(df["language"].unique()),
    default=sorted(df["language"].unique())
)

# Apply language filter to the DataFrame
filtered_by_language = df[df["language"].isin(languages)]

# Get unique options filtered by language and add "Select All" option
options = sorted(filtered_by_language["troopSchool"].unique())
options_with_select_all = ["Select All"] + options

# Troop filter with "Select All" option
troops = st.sidebar.multiselect(
    "Troop/School",
    options=options_with_select_all,
    default="Select All"
)

# Handle "Select All" logic
if "Select All" in troops:
    # If "Select All" is selected, select all options
    troops = options
else:
    # Remove "Select All" from the selection if it's not checked
    troops = [troop for troop in troops if troop != "Select All"]

# Date filters
min_date, max_date = pd.to_datetime(df["startDate"].dropna()).min(), pd.to_datetime(df["endDate"].dropna()).max()
default_date_range = (min_date, max_date)
date_range = st.sidebar.date_input(
    "Date Range",
    value=default_date_range,
    min_value=min_date,
    max_value=max_date
)

# Button to reset the date filter
if st.sidebar.button("Reset Date Filter"):
    date_range = default_date_range  # Update the date_range variable

# Apply filters
# 1, language filter
filtered_df = filtered_by_language.copy()

# 2, troop/school filter
filtered_df = filtered_df[filtered_df["troopSchool"].isin(troops)]

# 3, date range filter
start, end = date_range
filtered_df["startDate"] = pd.to_datetime(filtered_df["startDate"], errors="coerce")
filtered_df["endDate"] = pd.to_datetime(filtered_df["endDate"], errors="coerce")
filtered_df = filtered_df[(filtered_df["startDate"] >= pd.to_datetime(start)) & (filtered_df["startDate"] <= pd.to_datetime(end))]

# Check if the filtered DataFrame is empty
if filtered_df.empty:
    st.info("No records found for the selected filters.")
else:
    # Format the dates to 'YYYY-MM-DD'
    filtered_df["startDate"] = filtered_df["startDate"].dt.strftime('%Y-%m-%d')
    filtered_df["endDate"] = filtered_df["endDate"].dt.strftime('%Y-%m-%d')

    # Drop columns not needed for display
    filtered_df = filtered_df.drop(columns=["scrapeDate", "active"])

    # Rename columns for better display
    filtered_df = filtered_df.rename(columns={
        "language": "Language",
        "troopSchool": "Troop/School",
        "startDate": "Start Date",
        "endDate": "End Date"
    })

    # Show results
    st.subheader("Filtered Service Dates")
    st.dataframe(filtered_df, use_container_width=True)

st.write(f"Records: {len(filtered_df)}/{len(df)}")

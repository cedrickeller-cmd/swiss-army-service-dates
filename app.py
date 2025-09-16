# app.py
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "service_dates.db"

# Helper to load data from DB
@st.cache_data
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM activeServiceDates", conn)
        conn.close()
        return df
    except (sqlite3.OperationalError, pd.errors.DatabaseError) as e:
        # Database or table doesn't exist yet
        st.warning("No data available yet. Please run the scraper first to populate the database.")
        return pd.DataFrame(columns=["language", "troopSchool", "startDate", "endDate", "scrapeDate"])

# App layout
st.set_page_config(page_title="Swiss Army Service Dates", layout="wide")
st.title("Swiss Army Service Dates Lookup")

# Last updated info and data source caption
last_updated = pd.to_datetime(load_data()["scrapeDate"]).max().strftime('%a, %d %b %Y')
st.caption(f"**Last Updated:** {last_updated} |  **Data Sources:** [Schweizer Armee](https://www.armee.ch/de/aufgebotsdaten), [Armée Suisse](https://www.armee.ch/fr/dates-de-convocation), &amp; [Esercito Svizzero](https://www.armee.ch/it/date-di-chiamata-in-servizio)")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

# Language filter (single select to hide duplicates)
language = st.sidebar.selectbox(
    "Language",
    options=sorted(df["language"].unique()),
    index=0  # Default to first language
)

# Apply language filter to the DataFrame
filtered_by_language = df[df["language"] == language]

# Date filters
min_date, max_date = pd.to_datetime(df["startDate"].dropna()).min(), pd.to_datetime(df["endDate"].dropna()).max()
default_date_range = (min_date, max_date)

# Initialize date range in session state if not exists
if 'date_range' not in st.session_state:
    st.session_state.date_range = default_date_range

# Date input
date_range = st.sidebar.date_input(
    "Date Range",
    value=st.session_state.date_range,
    min_value=min_date,
    max_value=max_date
)

# Check if date_range is complete before filtering
try:
    if isinstance(date_range, tuple) and len(date_range) == 2:
        filter_start, filter_end = date_range
        # Apply filters
        filtered_df = filtered_by_language.copy()
        filtered_df["startDate"] = pd.to_datetime(filtered_df["startDate"], errors="coerce")
        filtered_df["endDate"] = pd.to_datetime(filtered_df["endDate"], errors="coerce")
        filtered_df = filtered_df[
            (filtered_df["startDate"] >= pd.to_datetime(filter_start)) & 
            (filtered_df["endDate"] <= pd.to_datetime(filter_end))
        ]
    else:
        st.sidebar.warning("Please select both start and end dates")
        filter_start, filter_end = default_date_range
        filtered_df = filtered_by_language.copy()
except ValueError:
    # Silently handle the ValueError
    filter_start, filter_end = default_date_range
    filtered_df = filtered_by_language.copy()

# Apply language filter to get available troops (without date filter)
available_troops = sorted(filtered_by_language["troopSchool"].unique())

# Initialize troops in session state if not exists
if 'troops' not in st.session_state:
    st.session_state.troops = ["Select All"]

# Reset to "Select All" if current selections are no longer valid
current_selections = [t for t in st.session_state.troops if t in available_troops or t == "Select All"]
if not current_selections or (len(current_selections) == 0):
    st.session_state.troops = ["Select All"]
else:
    st.session_state.troops = current_selections

# Create options list with "Select All"
options_with_select_all = ["Select All"] + available_troops

# Troop filter with "Select All" option
troops = st.sidebar.multiselect(
    "Troop/School",
    options=options_with_select_all,
    default=st.session_state.troops
)
#  dropdown becomes buggy with the session state -- when clicking a second option, it closes the dropdown and does only apply the first option
#  however, now it resets to "Select All" when i change the language filter or the date range
#  # Update session state
#  st.session_state.troops = troops

# Handle "Select All" logic
if "Select All" in troops:
    troops = available_troops
else:
    troops = [t for t in troops if t != "Select All"]

# Apply all filters to the final display DataFrame
filtered_df = filtered_by_language.copy()

# 1. Apply troop filter
filtered_df = filtered_df[filtered_df["troopSchool"].isin(troops)]

# 2. Apply date filter using the validated dates
filtered_df["startDate"] = pd.to_datetime(filtered_df["startDate"], errors="coerce")
filtered_df["endDate"] = pd.to_datetime(filtered_df["endDate"], errors="coerce")
filtered_df = filtered_df[
    (filtered_df["startDate"] >= pd.to_datetime(filter_start)) & 
    (filtered_df["endDate"] <= pd.to_datetime(filter_end))
]

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
    st.caption("**Tip:** Click on column headers to sort. Use the sidebar to adjust filters. Download the data using the menu in the top-right corner of the table.")
    st.dataframe(filtered_df, use_container_width=True)

st.write(f"Records: {len(filtered_df)}/{len(filtered_by_language)}")

# Add some vertical space
st.write("")
st.write("")

# Create footer
footer = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #262730;
    color: white; /* text color */
    padding: 10px;
    text-align: center;
    font-size: 0.8em;
}
.footer a {
    color: #ff4b4b;  /* primary red of streamlit theme for links */
    text-decoration: none;  /* Remove underline */
}
.footer a:hover {
    color: #e54343;  /* Darker red on hover */
    text-decoration: underline;  /* Add underline on hover */
}
</style>
<div class="footer">
    Developed with ❤️ by <a href="https://www.cedrickeller.ch/">C&eacutedric</a>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)

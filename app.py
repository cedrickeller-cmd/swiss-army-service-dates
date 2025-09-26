# app.py
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "data/service_dates.db"

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

# Load data
df = load_data()

# Last updated info and data source caption
last_updated = pd.to_datetime(df["scrapeDate"]).max().strftime('%a, %d %b %Y')
st.caption(f"**Last Updated:** {last_updated} |  **Data Sources:** [Schweizer Armee](https://www.armee.ch/de/aufgebotsdaten), [Armée Suisse](https://www.armee.ch/fr/dates-de-convocation), &amp; [Esercito Svizzero](https://www.armee.ch/it/date-di-chiamata-in-servizio)")

# Sidebar filters
st.sidebar.header("Filters")

# Language filter (single select to hide duplicates)
language = st.sidebar.selectbox(
    "Language",
    options=sorted(df["language"].unique()),
    index=0,  # Default to first language
    help="Select the language of the displayed Troop/School names"
)

# Apply language filter to the DataFrame
filtered_by_language = df[df["language"] == language]

# Date filters - Initialize session state for clearable date inputs
if 'date_start' not in st.session_state:
    st.session_state.date_start = None
if 'date_end' not in st.session_state:
    st.session_state.date_end = None

# Create two columns for start and end date
col1, col2 = st.sidebar.columns(2)

with col1:
    date_start = st.date_input(
        "Start Date",
        format="YYYY-MM-DD",
        value=None,
        key="date_start",
        help="Leave empty for no lower date limit"
    )

with col2:
    date_end = st.date_input(
        "End Date",
        value=None,
        key="date_end", 
        help="Leave empty for no upper date limit"
    )

# Apply date filtering based on selected values
filtered_df = filtered_by_language.copy()

# Convert date columns to datetime first
filtered_df["startDate"] = pd.to_datetime(filtered_df["startDate"], errors="coerce")
filtered_df["endDate"] = pd.to_datetime(filtered_df["endDate"], errors="coerce")

# Apply start date filter only if a date is selected
if date_start is not None:
    filtered_df = filtered_df[filtered_df["startDate"] >= pd.to_datetime(date_start)]

# Apply end date filter only if a date is selected  
if date_end is not None:
    filtered_df = filtered_df[filtered_df["endDate"] <= pd.to_datetime(date_end)]

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
    default=st.session_state.troops,
    help="Select one or more Troops/Schools. Use 'Select All' to select all options."
)

# Handle "Select All" logic
if "Select All" in troops:
    troops = available_troops
else:
    troops = [t for t in troops if t != "Select All"]

# Apply troop filter to the already date-filtered DataFrame
filtered_df = filtered_df[filtered_df["troopSchool"].isin(troops)]

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
    st.dataframe(filtered_df, width="stretch")

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

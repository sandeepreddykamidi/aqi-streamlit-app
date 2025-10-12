
# app.py
import streamlit as st
import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col
from typing import List

st.set_page_config(page_title="AQI Trend - By State/City/Day Level", layout="wide")
st.title("AQI Trend - By State / City / Day Level")
st.write("This Streamlit app reads AQI data from Snowflake (Snowpark)")

# Build Snowflake session from Streamlit secrets
# Note: streamlit secrets must contain a mapping "snowflake" with the Snowpark config keys.
# Example (how to set this is shown in deployment steps later):
# [snowflake]
# account = "xyz12345.us-east-1"
# user = "MY_USER"
# password = "MY_PASSWORD"
# role = "MY_ROLE"
# warehouse = "MY_WH"
# database = "DEV_DB"
# schema = "CONSUMPTION_SCH"
# session_parameters = {}
#
# IMPORTANT: Do not commit credentials to your repo; use Streamlit Cloud Secrets.
sf_configs = st.secrets.get("snowflake")
if not sf_configs:
    st.error(
        "Snowflake credentials not found in Streamlit Secrets. "
        "Open App > Settings > Secrets on Streamlit Cloud and add the 'snowflake' mapping."
    )
    st.stop()

# Create Snowpark session (cached to avoid reconnecting many times)
@st.cache_resource(ttl=3600)
def get_session(configs: dict) -> Session:
    return Session.builder.configs(configs).create()

session = get_session(sf_configs)

st.sidebar.header("Filters")

# Helper to run SQL and return list of single-column strings
def fetch_scalar_list(sql: str) -> List[str]:
    df = session.sql(sql).collect()
    # collect returns list of Row objects; convert to strings safely
    return [str(row[0]) for row in df]

# Fetch distinct states
state_query = """
    SELECT state
    FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL
    GROUP BY state
    ORDER BY 1 DESC
"""
try:
    state_list = fetch_scalar_list(state_query)
except Exception as e:
    st.error(f"Error fetching states from Snowflake: {e}")
    st.stop()

if not state_list:
    st.warning("No states found in the table DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL")
    st.stop()

state_option = st.sidebar.selectbox("Select State", state_list)

# When a state is selected, fetch cities
city_list = []
if state_option:
    city_query = f"""
        SELECT city
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL
        WHERE state = '{state_option.replace("'", "''")}'
        GROUP BY city
        ORDER BY 1 DESC
    """
    try:
        city_list = fetch_scalar_list(city_query)
    except Exception as e:
        st.error(f"Error fetching cities: {e}")
        st.stop()

if not city_list:
    st.warning("No cities found for the selected state.")
    st.stop()

city_option = st.sidebar.selectbox("Select City", city_list)

# When a city is selected, fetch measurement dates
date_list = []
if city_option:
    date_query = f"""
        SELECT DATE(measurement_time) AS measurement_date
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL
        WHERE state = '{state_option.replace("'", "''")}'
          AND city = '{city_option.replace("'", "''")}'
        GROUP BY measurement_date
        ORDER BY 1 DESC
    """
    try:
        date_list = fetch_scalar_list(date_query)
    except Exception as e:
        st.error(f"Error fetching dates: {e}")
        st.stop()

if not date_list:
    st.warning("No measurement dates found for the selected city.")
    st.stop()

date_option = st.sidebar.selectbox("Select Date", date_list)

# If date selected, fetch hourly trend
if date_option:
    trend_sql = f"""
    SELECT
        HOUR(measurement_time) AS hour,
        PM25_AVG,
        PM10_AVG,
        SO2_AVG,
        NO2_AVG,
        NH3_AVG,
        CO_AVG,
        O3_AVG
    FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL
    WHERE state = '{state_option.replace("'", "''")}'
      AND city  = '{city_option.replace("'", "''")}'
      AND DATE(measurement_time) = '{date_option}'
    ORDER BY measurement_time
    """
    try:
        rows = session.sql(trend_sql).collect()
    except Exception as e:
        st.error(f"Error fetching hourly trend: {e}")
        st.stop()

    if not rows:
        st.info("No hourly measurements found for the chosen state/city/date.")
    else:
        # Build a pandas DataFrame correctly from Snowpark Row objects
        col_names = ["Hour", "PM25", "PM10", "SO2", "NO2", "NH3", "CO", "O3"]
        # Convert rows to list of tuples
        records = [tuple(r) for r in rows]
        pd_df = pd.DataFrame.from_records(records, columns=col_names)

        # Show table and charts
        st.subheader(f"AQI hourly trend for {city_option}, {state_option} on {date_option}")
        st.dataframe(pd_df, use_container_width=True)

        # Bar chart for all pollutants (stacked by value per hour is not default; we will show separate charts)
        st.markdown("### Pollutant line charts by hour")
        # Line chart for PM2.5 and PM10
        cols_to_plot = ["PM25", "PM10", "SO2", "NO2", "NH3", "CO", "O3"]
        # Show each pollutant as an individual line chart to keep readability
        for pollutant in cols_to_plot:
            st.markdown(f"**{pollutant}**")
            chart_df = pd_df[["Hour", pollutant]].set_index("Hour")
            st.line_chart(chart_df)

st.sidebar.markdown("---")
st.sidebar.write("App connected to Snowflake using Streamlit Secrets (Snowpark).")

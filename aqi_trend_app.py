# Import Python packages
import streamlit as st
import pandas as pd
from snowflake.snowpark import Session

# Page Title
st.title("AQI Trend - By State / City / Day Level")
st.write("This Streamlit app is hosted on Streamlit Community Cloud and connects securely to Snowflake.")

# Create Snowflake session using Streamlit secrets
@st.cache_resource
def create_session():
    connection_parameters = st.secrets["connections.snowflake"]
    return Session.builder.configs(connection_parameters).create()

session = create_session()

# Initialize selection parameters
state_option, city_option, date_option = '', '', ''

# Query to get distinct states
state_query = """
    SELECT state 
    FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL 
    GROUP BY state 
    ORDER BY 1 DESC
"""
state_df = session.sql(state_query).to_pandas()
state_list = state_df["STATE"].tolist()

# Render selectbox for State
state_option = st.selectbox('Select State', state_list)

# City selection
if state_option:
    city_query = f"""
        SELECT city 
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL 
        WHERE state = '{state_option}'
        GROUP BY city 
        ORDER BY 1 DESC
    """
    city_df = session.sql(city_query).to_pandas()
    city_list = city_df["CITY"].tolist()
    city_option = st.selectbox('Select City', city_list)

# Date selection
if city_option:
    date_query = f"""
        SELECT DATE(measurement_time) AS measurement_date 
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL 
        WHERE state = '{state_option}' 
          AND city = '{city_option}'
        GROUP BY measurement_date 
        ORDER BY 1 DESC
    """
    date_df = session.sql(date_query).to_pandas()
    date_list = date_df["MEASUREMENT_DATE"].astype(str).tolist()
    date_option = st.selectbox('Select Date', date_list)

# Display trend data and charts
if date_option:
    trend_sql = f"""
        SELECT 
            HOUR(measurement_time) AS Hour,
            PM25_AVG,
            PM10_AVG,
            SO2_AVG,
            NO2_AVG,
            NH3_AVG,
            CO_AVG,
            O3_AVG
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL
        WHERE 
            state = '{state_option}' AND
            city = '{city_option}' AND 
            DATE(measurement_time) = '{date_option}'
        ORDER BY measurement_time
    """

    trend_df = session.sql(trend_sql).to_pandas()

    # Rename columns for clarity
    trend_df.columns = ['Hour', 'PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3']

    st.subheader(f"Air Quality Trend for {city_option}, {state_option} on {date_option}")
    st.bar_chart(trend_df, x='Hour', y=['PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3'])
    st.divider()
    st.line_chart(trend_df, x='Hour', y=['PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3'])

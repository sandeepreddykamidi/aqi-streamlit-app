# Import required libraries
import os
import streamlit as st
import pandas as pd
from snowflake.snowpark import Session

# Page Title
st.title("AQI Trend - By State / City / Day Level")
st.write("This Streamlit app is hosted on the Snowflake Cloud Data Warehouse Platform")

# Create Snowflake session using environment variables
connection_parameters = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
}

# Initialize Snowflake session
session = Session.builder.configs(connection_parameters).create()

# Initialize empty variables
state_option, city_option, date_option = '', '', ''

# Query to get distinct states
state_query = """
    SELECT state 
    FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL 
    GROUP BY state 
    ORDER BY 1 DESC
"""
state_df = session.sql(state_query).to_pandas()
state_list = state_df['STATE'].tolist()

# State selector
state_option = st.selectbox('Select State', state_list)

if state_option:
    # Query to get cities for the selected state
    city_query = f"""
        SELECT city 
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL 
        WHERE state = '{state_option}' 
        GROUP BY city 
        ORDER BY 1 DESC
    """
    city_df = session.sql(city_query).to_pandas()
    city_list = city_df['CITY'].tolist()
    city_option = st.selectbox('Select City', city_list)

if city_option:
    # Query to get available dates
    date_query = f"""
        SELECT DATE(measurement_time) AS measurement_date
        FROM DEV_DB.CONSUMPTION_SCH.AGG_CITY_FACT_HOUR_LEVEL
        WHERE state = '{state_option}' 
          AND city = '{city_option}'
        GROUP BY measurement_date
        ORDER BY 1 DESC
    """
    date_df = session.sql(date_query).to_pandas()
    date_list = date_df['MEASUREMENT_DATE'].astype(str).tolist()
    date_option = st.selectbox('Select Date', date_list)

if date_option:
    # Main trend query
    trend_sql = f"""
        SELECT 
            HOUR(measurement_time) AS HOUR,
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
    sf_df = session.sql(trend_sql).to_pandas()

    # Rename columns for better chart readability
    sf_df.columns = ['Hour', 'PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3']

    # Display charts
    st.bar_chart(sf_df, x='Hour', y=['PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3'])
    st.divider()
    st.line_chart(sf_df, x='Hour', y=['PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3'])

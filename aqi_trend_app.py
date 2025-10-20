# Import Python packages
import streamlit as st
import pandas as pd
from snowflake.snowpark import Session

# -------------------------------
# Page Title
st.title("Air Quality Trend - At Station Level")
st.write("This Streamlit app is hosted on Streamlit Community Cloud and connects securely to Snowflake.")

# -------------------------------
# Create Snowflake session using Streamlit secrets
@st.cache_resource
def create_session():
    connection_parameters = st.secrets["connections"]["snowflake"]
    session = Session.builder.configs(connection_parameters).create()
    return session

session = create_session()

# Initialize selection parameters
state_option, city_option, station_option, date_option = '', '', '', ''

# -------------------------------
# Query to get distinct states
state_query = """
    SELECT state 
    FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
    GROUP BY state 
    ORDER BY 1
"""
state_df = session.sql(state_query).to_pandas()
state_list = state_df["STATE"].tolist()
state_option = st.selectbox('Select State', state_list)

# -------------------------------
# City selection based on state
if state_option:
    city_query = f"""
        SELECT city 
        FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
        WHERE state = '{state_option}' 
        GROUP BY city 
        ORDER BY 1
    """
    city_df = session.sql(city_query).to_pandas()
    city_list = city_df["CITY"].tolist()
    city_option = st.selectbox('Select City', city_list)

# -------------------------------
# Station selection based on state & city
if city_option:
    station_query = f"""
        SELECT station 
        FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
        WHERE state = '{state_option}' AND city = '{city_option}'
        GROUP BY station 
        ORDER BY 1
    """
    station_df = session.sql(station_query).to_pandas()
    station_list = station_df["STATION"].tolist()
    station_option = st.selectbox('Select Station', station_list)

# -------------------------------
# Date selection based on state, city & station
if station_option:
    date_query = f"""
        SELECT DATE(measurement_time) AS measurement_date
        FROM DEV_DB.CONSUMPTION_SCH.AIR_QUALITY_FACT f
        JOIN DEV_DB.CONSUMPTION_SCH.LOCATION_DIM l 
            ON f.location_fk = l.location_pk
        WHERE state = '{state_option}' AND city = '{city_option}' AND station = '{station_option}'
        GROUP BY DATE(measurement_time)
        ORDER BY 1 DESC
    """
    date_df = session.sql(date_query).to_pandas()
    date_list = date_df["MEASUREMENT_DATE"].astype(str).tolist()
    date_option = st.selectbox('Select Date', date_list)

# -------------------------------
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
            O3_AVG,
            AQI
        FROM DEV_DB.CONSUMPTION_SCH.AIR_QUALITY_FACT f
        JOIN DEV_DB.CONSUMPTION_SCH.LOCATION_DIM l 
            ON f.location_fk = l.location_pk
        WHERE state = '{state_option}' AND city = '{city_option}' AND station = '{station_option}' 
          AND DATE(measurement_time) = '{date_option}'
        ORDER BY measurement_time
    """
    trend_df = session.sql(trend_sql).to_pandas()

    # Rename columns for clarity
    trend_df.columns = ['Hour', 'PM2.5', 'PM10', 'SO2', 'NO2', 'NH3', 'CO', 'O3', 'AQI']

    # -------------------------------
    # Charts
    st.subheader(f"Hourly AQI Level")
    st.line_chart(trend_df[['Hour', 'AQI']].set_index('Hour'))

    st.subheader(f"Stacked Chart: Hourly Pollutant Levels")
    st.bar_chart(trend_df.set_index('Hour')[['PM2.5','PM10','SO2','NO2','NH3','CO','O3']])

    st.subheader(f"Line Chart: Hourly Pollutant Levels")
    st.line_chart(trend_df.set_index('Hour')[['PM2.5','PM10','SO2','NO2','NH3','CO','O3']])

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
    SELECT DISTINCT state 
    FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
    ORDER BY state
"""
state_rows = session.sql(state_query).collect()
state_list = [row[0] for row in state_rows]
state_option = st.selectbox('Select State', state_list)

# -------------------------------
# City selection based on state
if state_option:
    city_query = f"""
        SELECT DISTINCT city 
        FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
        WHERE state = '{state_option}' 
        ORDER BY city
    """
    city_rows = session.sql(city_query).collect()
    city_list = [row[0] for row in city_rows]
    city_option = st.selectbox('Select City', city_list)

# -------------------------------
# Station selection based on state & city
if city_option:
    station_query = f"""
        SELECT DISTINCT station 
        FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
        WHERE state = '{state_option}' AND city = '{city_option}'
        ORDER BY station
    """
    station_rows = session.sql(station_query).collect()
    station_list = [row[0] for row in station_rows]
    station_option = st.selectbox('Select Station', station_list)

# -------------------------------
# Date selection based on state, city & station
if station_option:
    date_query = f"""
        SELECT DISTINCT TO_DATE(measurement_time) AS measurement_date
        FROM DEV_DB.CONSUMPTION_SCH.AIR_QUALITY_FACT f
        JOIN DEV_DB.CONSUMPTION_SCH.LOCATION_DIM l 
            ON f.location_fk = l.location_pk
        WHERE state = '{state_option}' 
          AND city = '{city_option}' 
          AND station = '{station_option}'
        ORDER BY measurement_date DESC
    """
    date_rows = session.sql(date_query).collect()
    date_list = [str(row[0]) for row in date_rows]
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
          AND TO_DATE(measurement_time) = '{date_option}'
        ORDER BY measurement_time
    """
    trend_rows = session.sql(trend_sql).collect()
    
    # Convert to pandas DataFrame
    trend_df = pd.DataFrame(trend_rows, columns=['Hour', 'PM2.5','PM10','SO2','NO2','NH3','CO','O3','AQI'])

    # -------------------------------
    # Charts
    st.subheader(f"Hourly AQI Level")
    st.line_chart(trend_df[['Hour', 'AQI']].set_index('Hour'))

    st.subheader(f"Stacked Chart: Hourly Pollutant Levels")
    st.bar_chart(trend_df.set_index('Hour')[['PM2.5','PM10','SO2','NO2','NH3','CO','O3']])

    st.subheader(f"Line Chart: Hourly Pollutant Levels")
    st.line_chart(trend_df.set_index('Hour')[['PM2.5','PM10','SO2','NO2','NH3','CO','O3']])

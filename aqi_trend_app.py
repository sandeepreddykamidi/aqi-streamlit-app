# Import Python packages
import streamlit as st
import pandas as pd
import snowflake.connector
from snowflake.snowpark import Session

# -------------------------------
# Page Title
st.title("Air Quality Trend - At Station Level")
st.write("This Streamlit app is hosted on Streamlit Community Cloud and connects securely to Snowflake.")

# -------------------------------
# Snowflake Connector for dropdowns
@st.cache_resource
def create_snowflake_conn():
    conn = snowflake.connector.connect(
        user=st.secrets["connections"]["snowflake"]["user"],
        password=st.secrets["connections"]["snowflake"]["password"],
        account=st.secrets["connections"]["snowflake"]["account"],
        warehouse=st.secrets["connections"]["snowflake"]["warehouse"],
        database=st.secrets["connections"]["snowflake"]["database"],
        schema=st.secrets["connections"]["snowflake"]["schema"]
    )
    return conn

conn = create_snowflake_conn()

# Snowpark session for trend queries
@st.cache_resource
def create_snowpark_session():
    session = Session.builder.configs(st.secrets["connections"]["snowflake"]).create()
    return session

session = create_snowpark_session()

# -------------------------------
# State selection
state_query = "SELECT DISTINCT state FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM ORDER BY state"
cur = conn.cursor()
cur.execute(state_query)
state_list = [row[0] for row in cur.fetchall()]
state_option = st.selectbox('Select State', state_list)

# -------------------------------
# City selection
city_option = ''
if state_option:
    city_query = f"""
        SELECT DISTINCT city 
        FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
        WHERE state = '{state_option}' 
        ORDER BY city
    """
    cur.execute(city_query)
    city_list = [row[0] for row in cur.fetchall()]
    city_option = st.selectbox('Select City', city_list)

# -------------------------------
# Station selection
station_option = ''
if city_option:
    station_query = f"""
        SELECT DISTINCT station 
        FROM DEV_DB.CONSUMPTION_SCH.LOCATION_DIM 
        WHERE state = '{state_option}' AND city = '{city_option}'
        ORDER BY station
    """
    cur.execute(station_query)
    station_list = [row[0] for row in cur.fetchall()]
    station_option = st.selectbox('Select Station', station_list)

# -------------------------------
# Date selection
date_option = ''
if station_option:
    date_query = f"""
        SELECT DISTINCT TO_DATE(measurement_time) AS measurement_date
        FROM DEV_DB.CONSUMPTION_SCH.AIR_QUALITY_FACT f
        JOIN DEV_DB.CONSUMPTION_SCH.LOCATION_DIM l
            ON f.location_fk = l.location_pk
        WHERE state = '{state_option}' AND city = '{city_option}' AND station = '{station_option}'
        ORDER BY measurement_date DESC
    """
    cur.execute(date_query)
    date_list = [str(row[0]) for row in cur.fetchall()]
    date_option = st.selectbox('Select Date', date_list)

# -------------------------------
# Display trend data and charts using Snowpark
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
    trend_df = pd.DataFrame(trend_rows, columns=['Hour','PM2.5','PM10','SO2','NO2','NH3','CO','O3','AQI'])

    # -------------------------------
    # Charts
    st.subheader(f"Hourly AQI Level")
    st.line_chart(trend_df[['Hour','AQI']].set_index('Hour'))

    st.subheader(f"Stacked Chart: Hourly Pollutant Levels")
    st.bar_chart(trend_df.set_index('Hour')[['PM2.5','PM10','SO2','NO2','NH3','CO','O3']])

    st.subheader(f"Line Chart: Hourly Pollutant Levels")
    st.line_chart(trend_df.set_index('Hour')[['PM2.5','PM10','SO2','NO2','NH3','CO','O3']])

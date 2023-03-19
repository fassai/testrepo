import streamlit as st
import pandas as pd
import plost 

st.set_page_config(layout='wide', initial_sidebar_state='expanded')

# Markdown 
st.title("Warrix Health Sale & Marketing Dashboard")
st.markdown("For internal use only")

st.sidebar.header('Dashboard `version 2`')

st.sidebar.subheader('Donut chart parameter')
donut_theta = st.sidebar.selectbox('Select data', ('q2', 'q3'))

st.sidebar.subheader('Line chart parameters')
plot_data = st.sidebar.multiselect('Select data', ['temp_min', 'temp_max'], ['temp_min', 'temp_max'])
plot_height = st.sidebar.slider('Specify plot height', 200, 500, 500)

st.sidebar.markdown('''
---
Created by Fasai Puengudom.
''')


# Row A
st.markdown('### Metrics')
col1, col2, col3 = st.columns(3)
col1.metric("Online Revenue", "14,700,000 THB", "12 %")
col2.metric("Offline Revenue", "36,300,000 THB", "40 %")
col3.metric("ROAS", "4:1", "+5%")

# Row B
seattle_weather = pd.read_csv('https://raw.githubusercontent.com/tvst/plost/master/data/seattle-weather.csv', parse_dates=['date'])
stocks = pd.read_csv('https://raw.githubusercontent.com/dataprofessor/data/master/stocks_toy.csv')

c1, c2 = st.columns((7,3))
with c1:
    st.markdown('### Line chart')
    st.line_chart(seattle_weather, x = 'date', y = plot_data, height = plot_height)
with c2:
    st.markdown('### Donut chart')
    plost.donut_chart(
        data=stocks,
        theta=donut_theta,
        color='company',
        legend='bottom', 
        use_container_width=True)
    
    #ok
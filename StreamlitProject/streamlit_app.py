import streamlit as st
import pandas as pd
import numpy as np
import plotly_express as px

# Markdown 
st.title("Twitter sentiment dashboard")
st.markdown("By Fasai P")

# Sidebar
st.sidebar.title("Twitter sentiment") 
st.sidebar.markdown("For those who care")

# Getting data 
DATA_URL = ("/Users/fasaisimacpro/Document/PythonPortfolio/StreamlitProject/Tweets.csv")
def load_data():
    data = pd.read_csv(DATA_URL)
    data['tweet_created'] = pd.to_datetime(data['tweet_created'])
    return data

data = load_data()

st.sidebar.subheader("Show random tweet")
random_tweet = st.sidebar.radio('Sentiment',('positive','neutral','negative'))
st.sidebar.markdown(data.query('airline_sentiment == @random_tweet')[["text"]].sample(n=1).iat[0,0])

st.sidebar.markdown("### Number of tweets by sentiment")
select = st.sidebar.selectbox('Visualization type', ['Histogram','Pie chart'], key='1')
sentiment_count = data['airline_sentiment'].value_counts()
sentiment_count = pd.DataFrame({'Sentiment': sentiment_count.index,'Tweets':sentiment_count.values})

if not st.sidebar.checkbox("Hide",True):
    st.markdown("### Number of tweets by sentiment")
    if select == "Histogram": 
        fig = px.bar(sentiment_count,x='Sentiment',y='Tweets',height=500)
        st.plotly_chart(fig)
    else:
        fig = px.pie(sentiment_count,values='Tweets',names='Sentiment')
        st.plotly_chart(fig)
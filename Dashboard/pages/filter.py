import streamlit as st
import pandas as pd
import seaborn as sns
import plotly.express as px 

df=sns.load_dataset('titanic')

st.set_page_config(page_title="TITANIC DATA ANALYTICS")
st.title("Titanic Survival Analysis Dashboard")
st.markdown("Explore the demographics and survival rates of the titanic passengers.")



















#pclass or passenger class
pclass=st.sidebar.multiselect(
    'Passenger Class',
    options=df['pclass'].unique(),
    default=df['pclass'].unique()
)

#age fi1ter
gender=st.sidebar.multiselect(
    'sex',
    options=df['sex'].unique(),
    default=df['sex'].unique()
)

min_age, max_age=st.sidebar.slider(
    "Age",
    min_value=int(df['age'].min()),
    max_value=int(df['age'].max()),
    value=(int(df['age'].min()), int(df['age'].max()))
)
embarked=st.sidebar.multiselect(
    'Embark Town',
    options=df['embark_town'].unique(),
    default=df['embark_town'].unique()
)
who=st.sidebar.multiselect(
    'who',
    options=df['who'].unique(),
    default=df['who'].unique()
)
    
filtered_df=df[(df['sex'].isin(gender))&(df['pclass'].isin(pclass))&(df['age']>=min_age)&(df['age']
<=max_age) & (df['embark_town'].isin(embarked))&(df['who'])]
st.markdown('### fiItered dataset')
st.dataframe(filtered_df)

#age distribution histogram
fig=px.histogram(filtered_df,x='age',title='Age Distribution Graph',nbins=50)
st.plotly_chart(fig,use_container_width=True)

#gender distribution graph
gender_count=filtered_df['sex'].value_counts()
fig2=px.pie(names=gender_count,values=gender_count.values,title='Gender Distribution')
st.plotly_chart(fig2,use_container_width=True)

fig3=px.sunburst( filtered_df,path=['class','sex','survived'],title='Titanic Survival Hierarchy')
st.plotly_chart(fig3,use_container_width=True)

fig4=px.scatter_matrix(df,dimensions=['age','sibsp','parch'])
st.plotly_chart(fig4,use_container_width=True)
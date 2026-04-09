import streamlit as st
import seaborn as sns
import plotly.express as px

st.title("Explore the Accidents Insights here")

df= sns.load_dataset("car_crashes")
st.dataframe(df)

fig =px.bar(df, x='abbrev', y='total',
            title = 'Total Accidents Statewise',
            labels = {'abbrev':'state','total':'total accidents'},
            template ='plotly_dark',
            color ='abbrev'
            )
st.plotly_chart(fig)
st.subheader('insights')

fig=px.bar(df,x='abbrev',y='total',title="Total car accidents by state",labels=
           {'abbrev':'state','total':'Total Accidents'})
st.plotly_chart(fig)
st.subheader('accidents')

top10= df.sort_values(by='ins_premium',ascending=False).head(10)
fig=px.bar(top10,x='abbrev',y='ins_premium',title='top 10 states by car insurance premium',
           labels={'abbrev':"States",'ins_premium':'Insurance Premium'},template='plotly_dark')
st.plotly_chart(fig)

fig=px.pie(df,values='speeding',names='abbrev',title='Percentage Of Speeding Car Accidents By State',template='plotly_dark')
fig.update_traces(textposition='inside',textinfo='percent+label')
st.plotly_chart(fig)

fig=px.scatter(df,x='alcohol',y='speeding',title='alchol vs speeding accidents by state',labels=
               {'alcohol':'Alcohol- Related Accidents','speeding':'Speeding-Related Accidents'},
               template='plotly_dark',size='total')
fig.update_layout(title={'x':0.5})
fig.update_layout(xaxis_title_font={'color':'red'},yaxis_title_font={'color':'green'})
st.plotly_chart(fig)

fig=px.line(df,x='abbrev',y='total',title='total car accidents by state',labels=
            {'abbrev':'States',"total":'Total Accidents'},template='plotly_dark',markers=True,
            line_shape='spline',color_discrete_sequence=px.colors.qualitative.Dark2)
st.plotly_chart(fig)
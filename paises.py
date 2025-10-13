import pandas as pd
import streamlit as st
import plotly.express as px

dataset = pd.read_csv("https://www.irdx.com.br/media/uploads/paises.csv")

st.dataframe(dataset)

fig = px.choropleth(dataset, 
                    locations=dataset ['iso3'],
                    color=dataset ['nome'], 
                    hover_name=dataset ['nome'])
fig.update_layout(title= 'Mapa Coroléptico dos Países', 
                  geo_scope='world')
st.plotly_chart (fig, use_container_width=True, the,e="streamlit")

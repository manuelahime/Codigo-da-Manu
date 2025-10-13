import pandas as pd
import streamlit as st

dataset = pd.read_csv("https://www.irdx.com.br/media/uploads/paises.csv")

st.dataframe(dataset)

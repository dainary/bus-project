import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
import folium
from streamlit_folium import st_folium

st.title("달서구 버스정류장 지도")

# 데이터
df = pd.read_excel("불편도 코딩 엑셀자료.xlsx", engine="openpyxl")

# 좌표 데이터 (너 CSV)
korea = pd.read_csv("국토교통부_전국 버스정류장 위치정보_20251031.csv")

korea["위도"] = pd.to_numeric(korea["위도"], errors="coerce")
korea["경도"] = pd.to_numeric(korea["경도"], errors="coerce")

coord = korea[["정류장명", "위도", "경도"]].dropna()

# 합치기
df["bus stop"] = df["bus stop"].astype(str).str.strip()
coord["정류장명"] = coord["정류장명"].astype(str).str.strip()

result = pd.merge(
    df,
    coord,
    left_on="bus stop",
    right_on="정류장명",
    how="left"
)

result = result.dropna(subset=["위도", "경도"])

# 지도
m = folium.Map(location=[35.829, 128.532], zoom_start=13)

for _, row in result.iterrows():

    folium.Marker(
        location=[row["위도"], row["경도"]],
        popup=row["bus stop"]
    ).add_to(m)

st_folium(m, width=1400, height=800)
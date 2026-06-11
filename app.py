import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
import folium
import json
from branca.element import Element
from streamlit_folium import st_folium

st.title("달서구 버스정류장 불편도 분석 지도")

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_bus_data():
    return pd.read_excel("불편도 코딩 엑셀자료.xlsx", engine="openpyxl")

@st.cache_data
def load_korea():
    return pd.read_csv("국토교통부_전국 버스정류장 위치정보_20251031.csv")

df = load_bus_data()
korea = load_korea()

# =========================
# 전처리
# =========================
df["bus stop"] = df["bus stop"].astype(str).str.strip()
korea["정류장명"] = korea["정류장명"].astype(str).str.strip()

korea["위도"] = pd.to_numeric(korea["위도"], errors="coerce")
korea["경도"] = pd.to_numeric(korea["경도"], errors="coerce")

coord = korea[["정류장명", "위도", "경도"]].dropna()

result = pd.merge(
    df,
    coord,
    left_on="bus stop",
    right_on="정류장명",
    how="left"
)

result = result.dropna(subset=["위도", "경도"])

# =========================
# 지도 생성 (완성본)
# =========================
@st.cache_resource
def make_map(data):

    m = folium.Map(location=[35.829, 128.532], zoom_start=13)

    search_data = []

    for _, row in data.iterrows():

        score = row.get("DiscomfortScore", 0)

        # =========================
        # 등급 + 색상
        # =========================
        if score >= 7:
            color = "red"
            grade = "어려움"
        elif score >= 5:
            color = "orange"
            grade = "보통"
        else:
            color = "green"
            grade = "쉬움"

        # =========================
        # 카카오맵 링크
        # =========================
        kakao_link = (
            f"https://map.kakao.com/link/map/"
            f"{row['bus stop']},{row['위도']},{row['경도']}"
        )

        # =========================
        # 분석 내용
        # =========================
        analysis = []

        if row.get("available space") == "X":
            analysis.append("여유공간 없음")

        if row.get("obstacle condition", 0) >= 2:
            analysis.append("장애물 존재")

        if row.get("illegal parking") == "O":
            analysis.append("불법주정차")

        if row.get("road condition", 0) >= 2:
            analysis.append("보도 상태 불량")

        if row.get("shelter type") in ["H", "C", "A"]:
            analysis.append("쉘터 상태 불량")

        if not analysis:
            analysis.append("전반적으로 양호")

        analysis_text = "<br>".join(["• " + x for x in analysis])

        # =========================
        # popup (완성형)
        # =========================
        popup = f"""
        <div style="width:300px; font-size:14px;">

        <b>정류장</b>: {row['bus stop']}<br>
        <b>불편도</b>: {round(score,2)}<br>
        <b>등급</b>: {grade}<br><br>

        <b>상세 분석</b><br>
        {analysis_text}<br><br>

        <a href="{kakao_link}" target="_blank"
           style="background:#FEE500;padding:6px 10px;
           border-radius:5px;text-decoration:none;">
           카카오맵 보기
        </a>

        </div>
        """

        folium.CircleMarker(
            location=[row["위도"], row["경도"]],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=popup
        ).add_to(m)

        # =========================
        # 검색 데이터
        # =========================
        search_data.append({
            "name": row["bus stop"],
            "lat": float(row["위도"]),
            "lng": float(row["경도"])
        })

    # =========================
    # 검색 UI
    # =========================
    search_json = json.dumps(search_data, ensure_ascii=False)
    map_name = m.get_name()

    search_html = f"""
    <div style="
        position: fixed;
        top: 10px;
        left: 60px;
        z-index:9999;
        background:white;
        padding:10px;
        border:1px solid gray;
        border-radius:6px;
    ">
        <input id="busSearch" placeholder="정류장 검색" style="width:200px;">
        <button onclick="searchBus()">검색</button>
    </div>

    <script>
    var busStops = {search_json};
    var map = {map_name};
    var marker = null;

    function searchBus() {{
        var keyword = document.getElementById("busSearch").value;

        for (var i=0; i<busStops.length; i++) {{
            if (busStops[i].name.includes(keyword)) {{

                map.setView([busStops[i].lat, busStops[i].lng], 16);

                if (marker) {{
                    map.removeLayer(marker);
                }}

                marker = L.marker([busStops[i].lat, busStops[i].lng]).addTo(map);
                marker.bindPopup(busStops[i].name).openPopup();

                return;
            }}
        }}

        alert("검색 결과 없음");
    }}
    </script>
    """

    m.get_root().html.add_child(Element(search_html))

    return m

# =========================
# 실행
# =========================
m = make_map(result)

st_folium(
    m,
    width=1400,
    height=800,
    key="map",
    returned_objects=[]
)
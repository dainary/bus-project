import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
from streamlit_folium import st_folium
import folium
import json
from branca.element import Element


st.write("1단계 통과")
st.write("앱 시작")


# =========================
# 1. 데이터 로딩 (캐시)
# =========================
@st.cache_data
def load_bus_data():
    return pd.read_excel(
        "불편도 코딩 엑셀자료.xlsx",
        engine="openpyxl"
    )

df = load_bus_data()   # ❗ 중복 제거 (이거 하나만 사용)


@st.cache_data
def load_korea():
    return pd.read_csv(
        "국토교통부_전국 버스정류장 위치정보_20251031.csv"
    )

korea = load_korea()


st.write("2단계 통과")


# =========================
# 2. (그대로 유지) 점수 계산
# =========================
# 👉 여기부터 아래는 네 코드 그대로 유지 (생략 없이 사용)


shelter_name = {
    "A": "기역자형",
    "B": "중간이 비어있는 기역자형",
    "C": "양면유리형",
    "D": "스마트쉘터",
    "E": "의자만 있는 유형",
    "F": "양면유리 없는 유형",
    "G": "의자 및 쉘터가 없는 유형",
    "H": "사방 밀폐형",
    "I": "대형정류장"
}

shelter_tbl = pd.DataFrame({
    "shelter type": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
    "shelter_sc": [7, 6, 8, 4, 2, 5, 1, 9, 3]
})

road_tbl = pd.DataFrame({
    "road condition": ["1", "2", "3"],
    "road_sc": [1, 2, 3]
})

park_tbl = pd.DataFrame({
    "illegal parking": ["O", "X"],
    "park_sc": [2,1]
})

obs_tbl = pd.DataFrame({
    "obstacle condition": ["1", "2", "3"],
    "obs_sc": [1, 2, 3]
})

space_tbl = pd.DataFrame({
    "available space": ["O", "X"],
    "space_sc": [1,2]
})

weight = {
    "illegal parking": 0.328,
    "obstacle condition": 0.262,
    "road condition": 0.180,
    "available space": 0.164,
    "shelter type": 0.066
}


shelter=[]; park=[]; space=[]; obstacle=[]; road=[]

for i in range(len(df)):
    for a in range(len(shelter_tbl)):
        if df["shelter type"][i] == shelter_tbl["shelter type"][a]:
            shelter.append(shelter_tbl["shelter_sc"][a] * weight["shelter type"])

for i in range(len(df)):
    for a in range(len(park_tbl)):
        if df["illegal parking"][i] == park_tbl["illegal parking"][a]:
            park.append(park_tbl["park_sc"][a] * weight["illegal parking"])

for i in range(len(df)):
    for a in range(len(space_tbl)):
        if df["available space"][i] == space_tbl["available space"][a]:
            space.append(space_tbl["space_sc"][a] * weight["available space"])

for i in range(len(df)):
    for a in range(len(obs_tbl)):
        if df["obstacle condition"][i] == int(obs_tbl["obstacle condition"][a]):
            obstacle.append(obs_tbl["obs_sc"][a] * weight["obstacle condition"])

for i in range(len(df)):
    for a in range(len(road_tbl)):
        if df["road condition"][i] == int(road_tbl["road condition"][a]):
            road.append(road_tbl["road_sc"][a] * weight["road condition"])


discomfort = []
for i in range(len(df)):
    discomfort.append(shelter[i] + park[i] + space[i] + obstacle[i] + road[i])

df["DiscomfortScore"] = discomfort / max(discomfort) * 10


# =========================
# 3. 이유 생성
# =========================
reason_list = []

for i in range(len(df)):
    reason = []

    reason.append(
        f"쉘터 형태 : {df['shelter type'][i]} ({shelter_name.get(df['shelter type'][i], '')})"
    )
    reason.append(f"보도 상태 : {df['road condition'][i]}")
    reason.append(f"불법주정차 : {df['illegal parking'][i]}")
    reason.append(f"장애물 상태 : {df['obstacle condition'][i]}")
    reason.append(f"여유공간 여부 : {df['available space'][i]}")

    reason_list.append("<br>".join(reason))

df["Reason"] = reason_list


st.write("3단계 통과")


# =========================
# 4. 좌표 결합
# =========================
dalseo = df.copy()

dalseo["bus stop"] = dalseo["bus stop"].astype(str).str.strip()
korea["정류장명"] = korea["정류장명"].astype(str).str.strip()

korea["위도"] = pd.to_numeric(korea["위도"], errors="coerce")
korea["경도"] = pd.to_numeric(korea["경도"], errors="coerce")

coord = korea[
    (korea["위도"].between(35.75, 35.90)) &
    (korea["경도"].between(128.45, 128.65))
][["정류장명", "위도", "경도"]]

coord = coord.drop_duplicates(subset=["정류장명"])

result = pd.merge(
    dalseo,
    coord,
    left_on="bus stop",
    right_on="정류장명",
    how="left"
)

result = result.drop(columns=["정류장명"])
result_map = result.dropna(subset=["위도", "경도"])


# =========================
# 5. 지도 캐싱 (🔥 핵심 수정)
# =========================
@st.cache_resource
def make_map(result_map):

    m = folium.Map(location=[35.829, 128.532], zoom_start=13)

    search_data = []

    for _, row in result_map.iterrows():

        score = row["DiscomfortScore"]

        if score >= 7.25:
            color = "red"
            grade = "어려움"
        elif score >= 6.5:
            color = "orange"
            grade = "보통"
        else:
            color = "green"
            grade = "쉬움"

        folium.CircleMarker(
            location=[float(row["위도"]), float(row["경도"])],
            radius=7,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=f"{row['bus stop']} | {round(score,2)} | {grade}"
        ).add_to(m)

        search_data.append({
            "name": row["bus stop"],
            "lat": float(row["위도"]),
            "lng": float(row["경도"])
        })

    search_json = json.dumps(search_data, ensure_ascii=False)

    map_name = m.get_name()

    search_html = f"""
    <div style="position:fixed;top:10px;left:60px;z-index:9999;background:white;padding:10px;border:2px solid gray;border-radius:5px;">
    <input id="busSearch" list="busList" placeholder="정류장명 검색" style="width:220px;">
    <datalist id="busList"></datalist>
    <button onclick="searchBus()">검색</button>
    </div>

    <script>
    var busStops = {search_json};
    var searchMarker = null;
    var datalist = document.getElementById("busList");

    busStops.forEach(function(stop){{
        var option = document.createElement("option");
        option.value = stop.name;
        datalist.appendChild(option);
    }});

    function searchBus() {{
        var keyword = document.getElementById("busSearch").value.trim();

        for(var i=0; i<busStops.length; i++) {{
            if(busStops[i].name.includes(keyword)) {{

                {map_name}.setView([busStops[i].lat, busStops[i].lng], 16);

                if(searchMarker){{
                    {map_name}.removeLayer(searchMarker);
                }}

                searchMarker = L.marker([busStops[i].lat, busStops[i].lng]).addTo({map_name});
                searchMarker.bindPopup(busStops[i].name).openPopup();
                return;
            }}
        }}

        alert("검색 결과 없음");
    }}
    </script>
    """

    m.get_root().html.add_child(Element(search_html))

    return m


m = make_map(result_map)


# =========================
# 6. 출력
# =========================
st.title("달서구 버스정류장 불편도 지도")

st_folium(
    m,
    width=1400,
    height=800,
    key="map"
)
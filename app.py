import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from branca.element import Element

st.set_page_config(layout="wide")

# =========================
# 1. 데이터 로딩 (클라우드 대응)
# =========================
@st.cache_data
def load_df():
    return pd.read_excel("불편도 코딩 엑셀자료.xlsx")

@st.cache_data
def load_korea():
    return pd.read_csv("국토교통부_전국 버스정류장 위치정보_20251031.csv")

# 파일 없을 때 안내
try:
    df = load_df()
    korea = load_korea()
except Exception as e:
    st.error("❌ 데이터 파일을 프로젝트 폴더에 넣어주세요.")
    st.stop()

# =========================
# 2. 점수 계산
# =========================
shelter_tbl = pd.DataFrame({
    "shelter type": ["A","B","C","D","E","F","G","H","I"],
    "shelter_sc": [7,6,8,4,2,5,1,9,3]
})

road_tbl = pd.DataFrame({
    "road condition": ["1","2","3"],
    "road_sc": [1,2,3]
})

park_tbl = pd.DataFrame({
    "illegal parking": ["O","X"],
    "park_sc": [2,1]
})

obs_tbl = pd.DataFrame({
    "obstacle condition": ["1","2","3"],
    "obs_sc": [1,2,3]
})

space_tbl = pd.DataFrame({
    "available space": ["O","X"],
    "space_sc": [1,2]
})

weight = {
    "illegal parking": 0.328,
    "obstacle condition": 0.262,
    "road condition": 0.180,
    "available space": 0.164,
    "shelter type": 0.066
}

# =========================
# 안전하게 벡터 방식 계산 (속도 + 안정성)
# =========================
df["shelter_sc"] = df["shelter type"].map(dict(zip(shelter_tbl["shelter type"], shelter_tbl["shelter_sc"])))
df["road_sc"] = df["road condition"].map(dict(zip(road_tbl["road condition"], road_tbl["road_sc"])))
df["park_sc"] = df["illegal parking"].map(dict(zip(park_tbl["illegal parking"], park_tbl["park_sc"])))
df["obs_sc"] = df["obstacle condition"].map(dict(zip(obs_tbl["obstacle condition"], obs_tbl["obs_sc"])))
df["space_sc"] = df["available space"].map(dict(zip(space_tbl["available space"], space_tbl["space_sc"])))

df["raw_score"] = (
    df["shelter_sc"] * weight["shelter type"] +
    df["road_sc"] * weight["road condition"] +
    df["park_sc"] * weight["illegal parking"] +
    df["obs_sc"] * weight["obstacle condition"] +
    df["space_sc"] * weight["available space"]
)

df["DiscomfortScore"] = df["raw_score"] / df["raw_score"].max() * 10

# =========================
# 3. 정류장 위치 매칭
# =========================
df["bus stop"] = df["bus stop"].astype(str).str.strip()
korea["정류장명"] = korea["정류장명"].astype(str).str.strip()

korea["위도"] = pd.to_numeric(korea["위도"], errors="coerce")
korea["경도"] = pd.to_numeric(korea["경도"], errors="coerce")

coord = korea[
    (korea["위도"].between(35.75, 35.90)) &
    (korea["경도"].between(128.45, 128.65))
][["정류장명","위도","경도"]].drop_duplicates()

result = df.merge(coord, left_on="bus stop", right_on="정류장명", how="left")
result = result.drop(columns=["정류장명"])

# =========================
# 4. 이유 생성
# =========================
def make_reason(row):
    return "<br>".join([
        f"쉘터: {row['shelter type']}",
        f"보도: {row['road condition']}",
        f"불법주정차: {row['illegal parking']}",
        f"장애물: {row['obstacle condition']}",
        f"여유공간: {row['available space']}"
    ])

result["Reason"] = result.apply(make_reason, axis=1)

# =========================
# 5. 지도 생성 (핵심)
# =========================
@st.cache_resource
def make_map(data):

    m = folium.Map(location=[35.829,128.532], zoom_start=13)

    search_data = []

    for _, row in data.dropna(subset=["위도","경도"]).iterrows():

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
            location=[row["위도"], row["경도"]],
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=f"""
            <b>{row['bus stop']}</b><br>
            점수: {round(score,2)}<br>
            등급: {grade}<br><br>
            {row['Reason']}
            """
        ).add_to(m)

        search_data.append({
            "name": row["bus stop"],
            "lat": row["위도"],
            "lng": row["경도"]
        })

    search_json = json.dumps(search_data, ensure_ascii=False)

    map_name = m.get_name()

    search_html = f"""
    <div style="position:fixed;top:10px;left:60px;z-index:9999;background:white;padding:10px;">
        <input id="busSearch" placeholder="정류장 검색">
        <button onclick="searchBus()">검색</button>
    </div>

    <script>
    var busStops = {search_json};
    var mapObj = {map_name};

    function searchBus() {{
        var keyword = document.getElementById("busSearch").value;

        for (var i=0;i<busStops.length;i++) {{
            if(busStops[i].name.includes(keyword)) {{
                mapObj.setView([busStops[i].lat,busStops[i].lng],16);
                return;
            }}
        }}
        alert("없음");
    }}
    </script>
    """

    m.get_root().html.add_child(Element(search_html))

    return m

m = make_map(result)

# =========================
# 6. 출력
# =========================
st.title("달서구 버스정류장 불편도 지도")

st_folium(m, width=1400, height=800, key="map")
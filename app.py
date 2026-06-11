import pandas as pd
import folium
import json
from branca.element import Element

# =========================
# 1. 데이터 불러오기
# =========================
df = pd.read_excel(
    r"C:\Users\Owner\Desktop\파이썬 프로젝트\불편도 코딩 엑셀자료.xlsx"
)

korea = pd.read_csv(
    r"C:\Users\Owner\Desktop\파이썬 프로젝트\국토교통부_전국 버스정류장 위치정보_20251031.csv"
)


# =========================
# 2. 점수 계산
# =========================
shelter_tbl = pd.DataFrame({
    "shelter type": ["A","B","C","D","E","F","G","H","I"],
    "shelter_sc": [7,6,8,4,2,5,1,9,3]
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

road_tbl = pd.DataFrame({
    "road condition": ["1","2","3"],
    "road_sc": [1,2,3]
})

weight = {
    "illegal parking": 0.328,
    "obstacle condition": 0.262,
    "road condition": 0.180,
    "available space": 0.164,
    "shelter type": 0.066
}


discomfort = []

for i in range(len(df)):

    s = shelter_tbl.loc[shelter_tbl["shelter type"] == df["shelter type"][i], "shelter_sc"].values[0]
    p = park_tbl.loc[park_tbl["illegal parking"] == df["illegal parking"][i], "park_sc"].values[0]
    o = obs_tbl.loc[obs_tbl["obstacle condition"] == str(df["obstacle condition"][i]), "obs_sc"].values[0]
    sp = space_tbl.loc[space_tbl["available space"] == df["available space"][i], "space_sc"].values[0]
    r = road_tbl.loc[road_tbl["road condition"] == str(df["road condition"][i]), "road_sc"].values[0]

    score = (
        s * weight["shelter type"] +
        p * weight["illegal parking"] +
        o * weight["obstacle condition"] +
        sp * weight["available space"] +
        r * weight["road condition"]
    )

    discomfort.append(score)

df["DiscomfortScore"] = discomfort
df["DiscomfortScore"] = df["DiscomfortScore"] / max(df["DiscomfortScore"]) * 10


# =========================
# 3. 위치 데이터 병합
# =========================
df["bus stop"] = df["bus stop"].astype(str).str.strip()
korea["정류장명"] = korea["정류장명"].astype(str).str.strip()

korea["위도"] = pd.to_numeric(korea["위도"], errors="coerce")
korea["경도"] = pd.to_numeric(korea["경도"], errors="coerce")

coord = korea[
    (korea["위도"].between(35.75, 35.90)) &
    (korea["경도"].between(128.45, 128.65))
].drop_duplicates(subset=["정류장명"])

result = pd.merge(df, coord, left_on="bus stop", right_on="정류장명", how="left")
result = result.drop(columns=["정류장명"])
result = result.dropna(subset=["위도","경도"])


# =========================
# 4. 색상 함수
# =========================
def get_color(score):
    if score >= 7:
        return "red", "어려움"
    elif score >= 5:
        return "orange", "보통"
    else:
        return "green", "쉬움"


# =========================
# 5. 지도 생성
# =========================
m = folium.Map(location=[35.829, 128.532], zoom_start=13)

search_data = []

for _, row in result.iterrows():

    color, grade = get_color(row["DiscomfortScore"])

    folium.CircleMarker(
        location=[row["위도"], row["경도"]],
        radius=6,
        color=color,
        fill=True,
        fill_opacity=0.8,
        popup=f"""
        <b>{row['bus stop']}</b><br>
        점수: {round(row['DiscomfortScore'],2)}<br>
        등급: {grade}
        """
    ).add_to(m)

    search_data.append({
        "name": row["bus stop"],
        "lat": row["위도"],
        "lng": row["경도"]
    })


# =========================
# 6. 검색 기능 JS
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
border:2px solid gray;
border-radius:5px;
">

<input id="busSearch" placeholder="정류장 검색">
<button onclick="searchBus()">검색</button>

</div>

<script>

var busStops = {search_json};
var map = {map_name};
var marker;

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


# =========================
# 7. 저장
# =========================
m.save("달서구_불편도지도.html")

print("완료")
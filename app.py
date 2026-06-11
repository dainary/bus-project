
import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
from streamlit_folium import st_folium

st.write("1단계 통과")
st.write("앱 시작")

@st.cache_data
def load_bus_data():
    return pd.read_excel(
        "불편도 코딩 엑셀자료.xlsx",
        engine="openpyxl"
    )

df = load_bus_data()


st.write("2단계 통과")
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


shelter=[]
park=[]
space=[]
obstacle=[]
road=[]

for i in range(0,len(df)):
    for a in range(0,len(shelter_tbl)): 
        if df["shelter type"][i]==shelter_tbl["shelter type"][a]:
            #(쉘터점수표["쉘터형태별 점수"][a])
            shelter.append(shelter_tbl["shelter_sc"][a] * weight["shelter type"])

for i in range(0,len(df)):
    for a in range(0,len(park_tbl)):
        if df["illegal parking"][i]==park_tbl["illegal parking"][a]:
            park.append(park_tbl["park_sc"][a] * weight["illegal parking"])            

for i in range(0,len(df)):
    for a in range(0,len(space_tbl)):
        if df["available space"][i]==space_tbl["available space"][a]:
            space.append(space_tbl["space_sc"][a] * weight["available space"])     
        
for i in range(0,len(df)):
    for a in range(0,len(obs_tbl)):
        if df["obstacle condition"][i]==int(obs_tbl["obstacle condition"][a]):
            obstacle.append(obs_tbl["obs_sc"][a] * weight["obstacle condition"]) 

for i in range(0,len(df)):
    for a in range(0,len(road_tbl)):
        if df["road condition"][i]==int(road_tbl["road condition"][a]):
            road.append(road_tbl["road_sc"][a] * weight["road condition"]) 

discomfort=[]

for i in range(0,len(df)):
    discomfort.append(shelter[i]+park[i]+space[i]+obstacle[i]+road[i])

max(discomfort)

df["DiscomfortScore"] = discomfort / max(discomfort) * 10



reason_list = []

for i in range(0, len(df)):

    reason = []

    reason.append(
    f"쉘터 형태 : {df['shelter type'][i]} "
    f"({shelter_name.get(df['shelter type'][i], '')})"
    )
    reason.append(f"보도 상태 : {df['road condition'][i]}")
    reason.append(f"불법주정차 : {df['illegal parking'][i]}")
    reason.append(f"장애물 상태 : {df['obstacle condition'][i]}")
    reason.append(f"여유공간 여부 : {df['available space'][i]}")

    reason_list.append("<br>".join(reason))

df["Reason"] = reason_list

top10 = df.nlargest(10, "DiscomfortScore")




@st.cache_data
def load_korea():
    return pd.read_csv(
        "국토교통부_전국 버스정류장 위치정보_20251031.csv"
    )

korea = load_korea()

dalseo = df.copy()

# 공백 제거
dalseo["bus stop"] = dalseo["bus stop"].astype(str).str.strip()
korea["정류장명"] = korea["정류장명"].astype(str).str.strip()

# 위도·경도 숫자형 변환
korea["위도"] = pd.to_numeric(korea["위도"], errors="coerce")
korea["경도"] = pd.to_numeric(korea["경도"], errors="coerce")

# 달서구 주변 좌표만 추출
coord = korea[
    (korea["위도"].between(35.75, 35.90)) &
    (korea["경도"].between(128.45, 128.65))
][["정류장명", "위도", "경도"]]

# 같은 이름의 정류장이 여러 개 있을 경우 첫 번째만 사용
coord = coord.drop_duplicates(subset=["정류장명"])

# 위도·경도 붙이기
result = pd.merge(
    dalseo,
    coord,
    left_on="bus stop",
    right_on="정류장명",
    how="left"
)
st.write("3단계 통과")
# 중복 컬럼 제거
result = result.drop(columns=["정류장명"])


import folium
import json
from branca.element import Element

# 위치 없는 정류장 제거
result_map = result.dropna(subset=["위도", "경도"])

# 지도 생성
@st.cache_resource
def make_map(result_map):
    
    m = folium.Map(
        location=[35.829, 128.532],
        zoom_start=13
    )
    
    # 검색용 데이터 저장
    search_data = []
    
    for _, row in result_map.iterrows():
    
        score = row["DiscomfortScore"]
        
        kakao_link = (
        f"https://map.kakao.com/link/map/"
        f"{row['bus stop']},{row['위도']},{row['경도']}"
     )
    
    # AI 분석 결과 생성
        analysis = []
        
        if row["available space"] == "X":
            analysis.append("여유공간이 없음")
        
        if row["obstacle condition"] >= 2:
            analysis.append("장애물이 존재함")
        
        if row["illegal parking"] == "O":
            analysis.append("불법주정차가 확인됨")
        
        if row["road condition"] >= 2:
            analysis.append("보도 상태 개선 필요")
        
        if row["shelter type"] in ["H","C","A" ]:
            analysis.append("쉘터 시설이 좋지 않음")
        
        if len(analysis) == 0:
            analysis.append("전반적인 접근성이 양호함")
        
        analysis_text = "<br>".join(
            ["• " + item for item in analysis]
        )
        
       
        # 등급 및 색상
        if score >= 7.25:
            color = "red"
            grade = "어려움"
    
        elif score >= 6.5:
            color = "orange"
            grade = "보통"
    
        else:
            color = "green"
            grade = "쉬움"
    
        # 마우스 올렸을 때 표시될 내용
        tooltip_text = f"""
        <div style="
            font-size:20px;
            font-weight:bold;
            padding:5px;
            white-space:nowrap;
        ">
            {row['bus stop']}
        </div>
        """
    
        # 원형 마커
        folium.CircleMarker(
            location=[float(row["위도"]), float(row["경도"])],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
    
            # 마우스 올리면 즉시 표시
            tooltip=folium.Tooltip(
                tooltip_text,
                sticky=True
            ),
    
            # 클릭하면 상세정보 표시
            popup=f"""
            <div style="width:380px; font-size:16px;">
            
            <b>정류장명</b> : {row['bus stop']}<br>
            <b>불편도 점수</b> : {round(score,2)}<br>
            <b>접근성 등급</b> : {grade}<br><br>
            
            <b>세부 현황</b><br>
            {row['Reason']}<br><br>
            
            <hr>
            
            <b>AI 분석 결과</b><br>
            {analysis_text}
            
            <br><br>
            
            <a href="{kakao_link}"
               target="_blank"
               style="
               background:#FEE500;
               color:black;
               padding:8px 12px;
               border-radius:5px;
               text-decoration:none;
               font-weight:bold;
               ">
            📍 카카오맵에서 위치 보기
            </a>
            
            </div>
            """
        ).add_to(m)
    
        # 검색용 데이터 저장
        search_data.append({
            "name": row["bus stop"],
            "lat": float(row["위도"]),
            "lng": float(row["경도"])
        })
    
    # Python → JavaScript 전달
    search_json = json.dumps(search_data, ensure_ascii=False)
    
    # 지도 객체 이름 가져오기
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
    
    <input
        id="busSearch"
        list="busList"
        placeholder="정류장명 검색"
        style="width:220px;"
    >
    
    
    <datalist id="busList">
    </datalist>
    
    <button onclick="searchBus()">
    검색
    </button>
    
    </div>
    
    <script>
    
    var busStops = {search_json};
    
    var searchMarker = null;
    
    var datalist =
        document.getElementById("busList");
    
    busStops.forEach(function(stop){{
        var option =
            document.createElement("option");
    
        option.value = stop.name;
    
        datalist.appendChild(option);
    }});
    
    document
    .getElementById("busSearch")
    .addEventListener("keypress", function(event) {{
    
        if(event.key === "Enter") {{
            searchBus();
        }}
    
    }});
    
    function searchBus() {{
    
        var keyword =
            document.getElementById("busSearch")
            .value
            .trim();
    
        for(var i=0; i<busStops.length; i++) {{
    
            if(busStops[i].name.includes(keyword)) {{
    
                {map_name}.setView(
                    [busStops[i].lat, busStops[i].lng],
                    16
                );
    
                if(searchMarker){{
                    {map_name}.removeLayer(searchMarker);
                }}
    
                searchMarker = L.marker(
                    [busStops[i].lat, busStops[i].lng]
                ).addTo({map_name});
    
                searchMarker.bindPopup(
                    "<b>" + busStops[i].name + "</b>"
                ).openPopup();
    
                return;
            }}
        }}
    
        alert("검색 결과가 없습니다.");
    }}
    
    </script>
    """
    
    m.get_root().html.add_child(Element(search_html))
    return m

# 저장
m = make_map(result_map)

st.title("달서구 버스정류장 불편도 지도")

st_folium(
    m,
    width=1400,
    height=800,
    key="map"
)


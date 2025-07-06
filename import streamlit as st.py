import streamlit as st
import pandas as pd
import math
import folium
import os
from folium.plugins import HeatMap
from streamlit_folium import folium_static
from pathlib import Path
from kisyoutyou_fetcher import fetch_weather_csv  # 別ファイルとして用意

# データパス
TOWN_CSV = 'miyazaki_city_with_latlon.csv'
STORE_CSV = 'miyazaki_5pachi_geocode.csv'
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="天候シミュレーション", layout="wide")
st.title("天候・時間・イベント対応 Huffモデルシミュレーション")

# ────────────── サイドバー：設定 ──────────────
st.sidebar.header("📡 気象データ取得 & パラメータ")

year = st.sidebar.number_input("年", value=2024, step=1)
month = st.sidebar.selectbox("月", list(range(1, 13)), index=6)
station_name = st.sidebar.text_input("観測所名", value="宮崎")
hour_label = st.sidebar.selectbox("時間帯", ["朝(8時)", "昼(12時)", "夜(18時)"])
hour_map = {"朝(8時)": 8, "昼(12時)": 12, "夜(18時)": 18}
hour = hour_map[hour_label]
alpha = st.sidebar.slider("距離減衰係数 α", 1.0, 3.0, 1.5, step=0.1)
area_filter = st.sidebar.text_input("住所絞り込みキーワード", "")

# ────────────── 気象CSV取得ボタン ──────────────
if st.sidebar.button("📥 気象データ取得"):
    try:
        weather_csv = fetch_weather_csv(year, month, "宮崎県", station_name, f"{year}_{month}_{station_name}_hourly.csv")
        st.session_state['weather_file'] = weather_csv
        st.success(f"✅ 取得成功: {weather_csv}")
    except Exception as e:
        st.error(f"取得失敗: {e}")

# ────────────── ファイルロード ──────────────
@st.cache_data
def load_data():
    df_town = pd.read_csv(TOWN_CSV, encoding='utf-8')
    df_raw = pd.read_csv(STORE_CSV, encoding='shift_jis')
    df_store = pd.DataFrame({
        'name': df_raw['ホール名'],
        'size': df_raw['P台数'] + df_raw['S台数'],
        'lat': df_raw['緯度'],
        'lon': df_raw['経度'],
    })
    return df_town, df_store

df_town, df_store = load_data()
if area_filter:
    df_town = df_town[df_town['address'].str.contains(area_filter)]

# ────────────── 天候ファクター自動推定 ──────────────
weather_factor = 1.0
df_weather = None

if 'weather_file' in st.session_state:
    df_weather = pd.read_csv(st.session_state['weather_file'], encoding='utf-8')
    row = df_weather[df_weather['時'] == hour]
    if not row.empty:
        row = row.iloc[0]
        precip = float(row['降水量(mm)']) if pd.notnull(row['降水量(mm)']) else 0.0
        weather_str = str(row['天気']) if pd.notnull(row['天気']) else ""
        if precip >= 10:
            weather_factor = 0.5
        elif '雨' in weather_str:
            weather_factor = 0.6
        elif '曇' in weather_str:
            weather_factor = 0.8
        elif '晴' in weather_str or '快晴' in weather_str:
            weather_factor = 1.0
        else:
            weather_factor = 0.9
st.sidebar.markdown(f"☁️ 推定天候ファクター：**{weather_factor:.2f}**")

# ────────────── Huffモデル計算 ──────────────
time_factors = {8: 0.7, 12: 0.93, 18: 0.8}
pop_factor = time_factors.get(hour, 1.0) * weather_factor
pop_dyn = df_town['population'] * pop_factor
pop_sum = pop_dyn.sum()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = map(math.radians, (lat1, lat2))
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

shares = []
for store in df_store.itertuples():
    dists = df_town.apply(lambda t: haversine(t['latitude'], t['longitude'], store.lat, store.lon) + 1e-6, axis=1)
    weights = store.size / (dists ** alpha)
    pij = weights / weights.sum()
    share = (pop_dyn * pij).sum() / pop_sum
    shares.append(share)

df_store['share'] = shares
max_share = max(shares)

# ────────────── 結果表示 ──────────────
st.subheader("📋 店舗シェア一覧")
st.dataframe(df_store[['name', 'share']].sort_values('share', ascending=False))

st.subheader("📊 シェア棒グラフ")
st.bar_chart(df_store.set_index('name')['share'])

st.subheader("🌡️ ヒートマップ（来店予測）")
visits_pred = []
for _, town in df_town.iterrows():
    dists = df_store.apply(lambda s: haversine(town['latitude'], town['longitude'], s.lat, s.lon) + 1e-6, axis=1)
    weights = df_store['size'] / (dists ** alpha)
    pij = weights / weights.sum()
    visits_pred.append((pop_dyn * pij).sum())
df_town['visits_pred'] = visits_pred
m1 = folium.Map(location=[df_town['latitude'].mean(), df_town['longitude'].mean()], zoom_start=12)
HeatMap(df_town[['latitude', 'longitude', 'visits_pred']].values.tolist(), radius=20).add_to(m1)
folium_static(m1, width=800, height=450)

st.subheader("🔴 バブルマップ（店舗シェア）")
m2 = folium.Map(location=[df_town['latitude'].mean(), df_town['longitude'].mean()], zoom_start=12)
for store in df_store.itertuples():
    r = (store.share / max_share) * 300
    folium.Circle(location=[store.lat, store.lon], radius=r, fill=True, fill_opacity=0.6).add_to(m2)
folium_static(m2, width=800, height=450)

# ────────────── 保存処理 ──────────────
fname_tag = f"{station_name}_{hour}h_alpha{alpha:.1f}"
csv_path = OUTPUT_DIR / f"share_{fname_tag}.csv"
html_path = OUTPUT_DIR / f"bubblemap_{fname_tag}.html"

df_store[['name', 'share']].to_csv(csv_path, index=False, encoding='utf-8-sig')
m2.save(str(html_path))

st.success(f"✅ 結果を保存しました：{csv_path.name}, {html_path.name}")

# ダウンロードリンク
with open(csv_path, "rb") as f:
    st.download_button("📥 店舗シェアCSVをダウンロード", f, file_name=csv_path.name)

with open(html_path, "rb") as f:
    st.download_button("📥 バブルマップHTMLをダウンロード", f, file_name=html_path.name)

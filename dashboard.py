# dashboard.py
import streamlit as st
import pandas as pd
import glob
from pathlib import Path
import math
import folium
from streamlit_folium import folium_static
import streamlit.components.v1 as components

# ───────────────────────────────────────────────────────────
# 1. 定数・ファイルパス設定
# ───────────────────────────────────────────────────────────
MAP_DIR         = Path(".")
HEATMAP_DIR     = MAP_DIR / "huff_alpha_maps"
FLOW_MAP        = MAP_DIR / "flows_per_store_map.html"
STORE_GEO_CSV   = MAP_DIR / "miyazaki_5pachi_geocode.csv"
TOWN_CENTROID_CSV = MAP_DIR / "miyazaki_city_with_latlon.csv"

# ───────────────────────────────────────────────────────────
# 2. ページ設定
# ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Huffモデル BI ダッシュボード",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("Huffモデル BI ダッシュボード")
st.markdown("#### 時刻・α・エリアを動かして多様な可視化データを一画面で確認できます")

# ───────────────────────────────────────────────────────────
# 3. サイドバー：パラメータ入力
# ───────────────────────────────────────────────────────────
st.sidebar.header("🔧 パラメータ設定")

# 曜日
day_type = st.sidebar.selectbox("曜日", ["weekday", "weekend"])

# 時刻帯
time_slot = st.sidebar.selectbox("時間帯", ["morning", "noon", "evening"])

# α（ヒートマップ生成済みファイルから候補を自動取得）
heat_files = glob.glob(str(HEATMAP_DIR / "huff_map_alpha_*.html"))
available_alphas = sorted(
    { Path(fp).stem.split("_")[-1] for fp in heat_files },
    key=lambda x: float(x)
)
if len(available_alphas) > 1:
    alpha = st.sidebar.slider(
        "距離減衰係数 α",
        float(available_alphas[0]),
        float(available_alphas[-1]),
        float(available_alphas[0]),
        step=0.1
    )
else:
    alpha = float(available_alphas[0]) if available_alphas else 1.5
    st.sidebar.markdown(f"**距離減衰係数 α: {alpha}**")

# エリア絞り込み（住所に含む文字列）
area_filter = st.sidebar.text_input("エリア絞り込み", "")

# ───────────────────────────────────────────────────────────
# 4. データ読み込み
# ───────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    # 町丁データ
    df_town = pd.read_csv(TOWN_CENTROID_CSV, encoding='utf-8')
    # 店舗データ
    df_raw = pd.read_csv(STORE_GEO_CSV, encoding='shift_jis')
    df_store = pd.DataFrame({
        'name': df_raw['ホール名'],
        'size': df_raw['P台数'] + df_raw['S台数'],
        'lat':  df_raw['緯度'],
        'lon':  df_raw['経度'],
    })
    return df_town, df_store

df_town, df_store = load_data()

# 住所フィルタ
if area_filter:
    df_town = df_town[df_town['address'].str.contains(area_filter)]

# ───────────────────────────────────────────────────────────
# 5. Huffモデルによるシェア再計算（バブル用）
# ───────────────────────────────────────────────────────────
# （ヒートマップは既存HTMLを参照するため再計算不要）

# 動的人口ファクター例
time_factors = {'weekday':{'morning':0.7,'noon':0.93,'evening':0.8},
                'weekend':{'morning':0.5,'noon':1.0, 'evening':0.85}}
pop_factor = time_factors[day_type][time_slot]

# 距離計算関数
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 動的人口
pop_dyn = df_town['population'] * pop_factor
pop_sum = pop_dyn.sum()

shares = []
for store in df_store.itertuples():
    dists = df_town.apply(
        lambda t: haversine(t['latitude'], t['longitude'], store.lat, store.lon)+1e-6,
        axis=1
    )
    weights = store.size / (dists**float(alpha))
    pij = weights / weights.sum()
    share = (pop_dyn * pij).sum() / pop_sum
    shares.append(share)

df_store['share'] = shares
max_share = max(shares)

# ───────────────────────────────────────────────────────────
# 6. 可視化表示（縦並び）
# ───────────────────────────────────────────────────────────

# 6-1 テーブル
st.subheader("📋 店舗シェア一覧テーブル")
st.dataframe(
    df_store[['name','share']]
    .sort_values('share', ascending=False)
    .reset_index(drop=True),
    use_container_width=True
)

# 6-2 棒グラフ
st.subheader("📊 店舗シェア比較（棒グラフ）")
st.bar_chart(
    df_store.set_index('name')['share'],
    use_container_width=True
)

# 6-3 ヒートマップ（αごとに事前生成したHTML）
st.subheader("🌡️ ヒートマップ (α = %s)" % alpha)
heatmap_file = HEATMAP_DIR / f"huff_map_alpha_{alpha}.html"
if heatmap_file.exists():
    components.html(
        heatmap_file.read_text('utf-8'),
        height=600
    )
else:
    st.error("ヒートマップファイルがありません：%s" % heatmap_file.name)

# 6-4 バブルマップ
st.subheader(f"🔴 バブルマップ ({day_type}, {time_slot})")
bubble_file = MAP_DIR / f"bubble_map_{day_type}_{time_slot}.html"
if bubble_file.exists():
    components.html(
        bubble_file.read_text('utf-8'),
        height=600
    )
else:
    st.warning("バブルマップがありません：%s" % bubble_file.name)

# 6-5 店舗間フロー図
st.subheader("🔄 店舗間フロー図")
if FLOW_MAP.exists():
    components.html(
        FLOW_MAP.read_text('utf-8'),
        height=600
    )
else:
    st.error("フロー図がありません：flows_per_store_map.html")

st.markdown("---")
st.markdown("※ 各種マップは事前に生成したHTMLを読み込んでいます。")

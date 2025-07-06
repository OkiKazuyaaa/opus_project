# -*- coding: utf-8 -*-
"""
scenario_dashboard_complete.py  (compat v1.1)
──────────────────────────────────────────────────────────────────────
Streamlit アプリ: 多層 Huff モデル + 年齢層 + 天候 + P/S 比率 + イベント + ROI + 履歴
必要と思われる機能をすべて 1 ファイルにまとめたフル版。

🔄 2025‑05‑16  修正版
    • st.experimental_rerun が存在しない環境への互換ラッパ関数 `st_rerun()` を追加
    • 既存の `st.experimental_rerun()` 呼び出しをすべて `st_rerun()` へ置換
    • ストリームリット新旧 API の差異を吸収

動作要件
-----------
- Python 3.8+
- streamlit 1.10 以上推奨（古いバージョンでも起動可）
- pandas, numpy, folium, streamlit_folium, python-dotenv (任意)
- OpenWeatherMap API キー (環境変数 OPENWEATHER_API_KEY)

使用方法
-----------
$ streamlit run scenario_dashboard_complete.py
"""
from __future__ import annotations

from pathlib import Path
import math
import typing as t
import os
import json
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import streamlit as st
from folium.plugins import HeatMap
import folium
from streamlit_folium import folium_static
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────
# 互換ラッパ: Streamlit 再実行 (rerun)
# ──────────────────────────────────────────────────────────

def st_rerun() -> None:
    """Streamlit のバージョン差異を吸収して再実行する。"""
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    elif hasattr(st, "rerun"):
        st.rerun()  # type: ignore[attr-defined]
    else:
        st.warning("この Streamlit では rerun() が利用できません。ページを手動で再読み込みしてください。")

# ──────────────────────────────────────────────────────────
# 設定 / 定数
# ──────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
DATA_DIR        = BASE_DIR / "data"
OUTPUT_DIR      = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TOWN_CSV        = DATA_DIR / "miyazaki_city_with_latlon.csv"     # 町丁
STORE_CSV       = DATA_DIR / "miyazaki_5pachi_geocode.csv"       # ホール
AGE_CSV         = DATA_DIR / "miyazakishizinnkou.csv"            # 年齢別人口
EVENT_CSV       = DATA_DIR / "miyazaki_events.csv"               # イベント一覧 (日付・場所・来客数推計)
FLOW_MAP_HTML   = DATA_DIR / "flow_lines_map.html"               # 既存 HTML

# ──────────────────────────────────────────────────────────
# 環境変数読込 (.env 可)
# ──────────────────────────────────────────────────────────
load_dotenv(DATA_DIR / ".env")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ──────────────────────────────────────────────────────────
# Streamlit ページ設定
# ──────────────────────────────────────────────────────────
st.set_page_config(page_title="多層Huffモデルダッシュボード", layout="wide")
st.title("🗺 年齢層 × 天候 × Huffモデル 統合ダッシュボード (Full) ")

# ──────────────────────────────────────────────────────────
# サイドバー UI
# ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📡 パラメータ設定")

    # (1) 日付 & 観測所
    default_date = datetime.today()
    target_date  = st.date_input("分析日", value=default_date)
    station_name = st.text_input("気象観測所", "宮崎")

    # (2) 時間帯 & 距離減衰係数
    hour_label = st.selectbox("時間帯", ["朝(8時)", "昼(12時)", "夜(18時)"])
    hour_map   = {"朝(8時)": 8, "昼(12時)": 12, "夜(18時)": 18}
    hour       = hour_map[hour_label]
    alpha      = st.slider("距離減衰係数 α", 1.0, 3.0, 1.5, 0.1)

    # (3) フィルタ
    area_filter  = st.text_input("住所フィルタ", "")
    search_query = st.text_input("🔍 店舗名検索", "")

    # (4) 年齢層
    age_layers = ["全体", "20s", "30s", "40s", "50s", "60s以上"]
    age_choice = st.selectbox("対象年齢層", age_layers)

    # (5) P/S 台数閾値
    ps_ratio_min, ps_ratio_max = st.slider("P／S 台数比率", 0.0, 1.0, (0.0, 1.0))

    # (6) イベント補正ON/OFF
    enable_event = st.checkbox("イベント補正を適用", value=True)

    # (7) 履歴削除
    if st.button("履歴クリア"):
        st.session_state.pop("history", None)
        st.toast("履歴を削除しました", icon="🗑️")
        st_rerun()

# ──────────────────────────────────────────────────────────
# データ読込 & 前処理
# ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_town  = pd.read_csv(TOWN_CSV)
    df_store = pd.read_csv(STORE_CSV, encoding="shift_jis").rename(columns={
        "ホール名": "name", "P台数": "P", "S台数": "S", "緯度": "lat", "経度": "lon"})
    df_store["size"]   = df_store["P"] + df_store["S"]
    df_store["ps_ratio"] = df_store["P"] / df_store["size"]

    df_age   = pd.read_csv(AGE_CSV)
    if EVENT_CSV.exists():
        df_event = pd.read_csv(EVENT_CSV, parse_dates=["date"])
    else:
        df_event = pd.DataFrame(columns=["date", "address", "impact"])
    return df_town, df_store, df_age, df_event

df_town, df_store, df_age, df_event = load_data()

# --- 検索フィルタ適用
if area_filter:
    df_town = df_town[df_town["address"].str.contains(area_filter, na=False)]

if search_query:
    df_store = df_store[df_store["name"].str.contains(search_query, na=False)]

# P/S 比率フィルタ
ps_lower, ps_upper = ps_ratio_min, ps_ratio_max
mask_ps = df_store["ps_ratio"].between(ps_lower, ps_upper)
df_store = df_store[mask_ps]

# ──────────────────────────────────────────────────────────
# 天候ファクター
# ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_weather_factor(date: datetime, station: str) -> float:
    """OpenWeatherMap API から降水量などを取得しファクターを返す。"""
    if not OPENWEATHER_API_KEY:
        return 1.0  # API キー無し → ファクター 1
    try:
        import requests
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?q={station}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"  # noqa: E501
        )
        res = requests.get(url, timeout=5)
        data = res.json()
        rain_mm = data.get("rain", {}).get("1h", 0)
        clouds  = data.get("clouds", {}).get("all", 0) / 100  # 0‑1
        factor  = max(0.5, 1.0 - rain_mm * 0.03 - clouds * 0.2)
        return round(factor, 2)
    except Exception as e:  # noqa: BLE001
        st.error(f"天候データ取得失敗: {e}")
        return 1.0

weather_factor = fetch_weather_factor(target_date, station_name)
st.sidebar.markdown(f"☁️ **天候ファクター: {weather_factor:.2f}**")

# ──────────────────────────────────────────────────────────
# 年齢層別人口
# ──────────────────────────────────────────────────────────
if age_choice == "全体":
    base_pop = df_town["population"].values
else:
    age_col_map = {
        "20s": "pop_20s", "30s": "pop_30s", "40s": "pop_40s",
        "50s": "pop_50s", "60s以上": "pop_60plus"}
    base_pop = (
        df_age.set_index("address")[age_col_map[age_choice]]
        .reindex(df_town["address"])  # align
        .fillna(0)
        .values
    )

# 時間帯補正 & 天候補正
TIME_FACTORS = {8: 0.70, 12: 0.93, 18: 0.80}
active_pop   = base_pop * TIME_FACTORS[hour] * weather_factor

# ──────────────────────────────────────────────────────────
# イベント補正
# ──────────────────────────────────────────────────────────
if enable_event and not df_event.empty:
    mask_ev = df_event["date"] == pd.Timestamp(target_date)
    for _, ev in df_event[mask_ev].iterrows():
        # 町丁をキーに人口を上乗せ (単純加算モデル)
        idx = df_town["address"] == ev["address"]
        active_pop[idx] += ev["impact"]

pop_sum = active_pop.sum()

# ──────────────────────────────────────────────────────────
# Huff モデル
# ──────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    φ1, φ2 = map(math.radians, (lat1, lat2))
    dφ     = math.radians(lat2 - lat1)
    dλ     = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calc_store_share(store: pd.Series) -> float:
    """店舗毎の来店シェアを Huff + α で算出。"""
    d = df_town.apply(
        lambda t: haversine(t["latitude"], t["longitude"], store.lat, store.lon) + 1e-6,
        axis=1,
    )
    w = store.size / (d ** alpha)
    p = w / w.sum()
    return float((active_pop * p).sum() / pop_sum)


df_store["share"] = df_store.apply(calc_store_share, axis=1)

# ──────────────────────────────────────────────────────────
# 競合バッファ & ROI 試算
# ──────────────────────────────────────────────────────────

def competitor_load(row: pd.Series, radius_km: float = 1.5) -> int:
    """半径 radius_km 内の競合店舗総台数を返す"""
    def _within(s):
        return haversine(row.lat, row.lon, s.lat, s.lon) < radius_km
    return int(df_store[df_store.apply(_within, axis=1)]["size"].sum())


def calc_roi(store: pd.Series, investment_per_seat: int = 500000) -> tuple[int, float]:
    """投資額 (円) と単純 ROI (%) を返す"""
    investment = store.size * investment_per_seat
    yearly_gain = store.share * pop_sum * 2_000  # 1 来店あたり ¥2,000 消費想定
    roi = (yearly_gain - investment) / investment * 100
    return investment, round(roi, 1)


df_store["nearby_seats"] = df_store.apply(competitor_load, axis=1)
df_store[["investment_yen", "roi_pct"]] = df_store.apply(
    lambda s: pd.Series(calc_roi(s)), axis=1
)

# ──────────────────────────────────────────────────────────
# 可視化
# ──────────────────────────────────────────────────────────

st.subheader("📋 店舗シェア & ROI 一覧")
view_cols = ["name", "share", "roi_pct", "investment_yen", "nearby_seats"]
st.dataframe(
    df_store[view_cols].sort_values("share", ascending=False),
    use_container_width=True,
)

st.bar_chart(df_store.set_index("name")["share"])

# ヒートマップ
m_heat = folium.Map(
    location=[df_town["latitude"].mean(), df_town["longitude"].mean()], zoom_start=12
)
HeatMap(df_town[["latitude", "longitude"]].assign(weight=active_pop).values.tolist(), radius=18).add_to(m_heat)
folium_static(m_heat, width=800, height=450)

# バブルマップ
m_bubble = folium.Map(
    location=[df_town["latitude"].mean(), df_town["longitude"].mean()], zoom_start=12
)
max_share = df_store["share"].max()
for s in df_store.itertuples():
    radius   = (s.share / max_share) * 400
    folium.Circle(
        location=[s.lat, s.lon], radius=radius,
        popup=f"{s.name}: {s.share:.2%}",
        fill=True, fill_color="blue", fill_opacity=0.4, color="blue", opacity=0.6,
    ).add_to(m_bubble)
folium_static(m_bubble, width=800, height=450)

# ──────────────────────────────────────────────────────────
# 来店予測ランキング & 出店候補
# ──────────────────────────────────────────────────────────

df_town["visits_pred"] = active_pop
if "area_km2" in df_town.columns:
    df_town["pred_density"] = df_town["visits_pred"] / df_town["area_km2"]
else:
    df_town["pred_density"] = df_town["visits_pred"]

st.subheader("🏙 来店密度トップ30 町丁")
st.dataframe(
    df_town.sort_values("pred_density", ascending=False)[["address", "pred_density"]].head
)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_catchment_map.py

ステップ3の全結果 Excel から
キャッチメントエリア（勝ち取った起点）を
Folium 地図上に可視化します。
"""

import pandas as pd
import folium
import itertools
from folium import FeatureGroup, LayerControl

# ───── 設定 ─────
INPUT_FILE     = "huff_step3_all_in_one.xlsx"
DETAIL_SHEET   = "flows_detail"    # origin_id, origin_lat, origin_lon, store, P_ij, flow など
STORE_SHEET    = "flows_by_store"  # store, expected_visitors
OUTPUT_HTML    = "catchment_map.html"

# ───── データ読み込み ─────
# (1) 起点単位の詳細結果
df_det = pd.read_excel(INPUT_FILE, sheet_name=DETAIL_SHEET)
# 緯度経度がない行は除外
df_det = df_det.dropna(subset=["origin_lat", "origin_lon"])

# (2) 各起点で最も P_ij が大きい店舗をキャッチメントとみなす
df_det["rank"] = df_det.groupby("origin_id")["P_ij"].rank(method="first", ascending=False)
df_catch = df_det[df_det["rank"] == 1].copy()

# (3) 店舗位置（flows_by_store には緯度経度が入っていないはずなので
#     df_det から店舗ごとの代表緯度経度を取ってきます）
stores_pos = (
    df_det
    .groupby("store", as_index=False)
    .agg({
        "shop_lat": ("origin_lat", "mean"),
        "shop_lon": ("origin_lon", "mean")
    })
)

# ───── カラーパレット準備 ─────
stores = df_catch["store"].unique()
# 固定長のカラーパレットから自動割当
palette = {}
# Folium にあらかじめ用意されている12色サイクルを使います
color_cycle = itertools.cycle([
    "blue", "green", "red", "purple", "orange", "darkred",
    "lightred", "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple"
])
for st in stores:
    palette[st] = next(color_cycle)

# ───── Folium 地図生成 ─────
# 地図の中心は全起点の平均位置
center_lat = df_catch["origin_lat"].mean()
center_lon = df_catch["origin_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

# ───── キャッチメント起点を店舗ごとにプロット ─────
for st in stores:
    fg = FeatureGroup(name=f"Catchment: {st}", show=False)
    sub = df_catch[df_catch["store"] == st]
    for _, row in sub.iterrows():
        folium.CircleMarker(
            location=[row["origin_lat"], row["origin_lon"]],
            radius=4,
            color=palette[st],
            fill=True,
            fill_opacity=0.6,
            weight=0,
            popup=f"{st}\nP_ij={row['P_ij']:.3f}\nflow={row['flow']:.1f}"
        ).add_to(fg)
    fg.add_to(m)

# ───── 店舗位置を大きめマーカーでプロット ─────
for _, row in stores_pos.iterrows():
    folium.Marker(
        location=[row["shop_lat"], row["shop_lon"]],
        popup=row["store"],
        icon=folium.Icon(color="black", icon="home", prefix="fa")
    ).add_to(m)

# ───── レイヤーコントロール ─────
LayerControl(collapsed=False).add_to(m)

# ───── ファイル出力 ─────
m.save(OUTPUT_HTML)
print(f"完了: {OUTPUT_HTML} を出力しました。")

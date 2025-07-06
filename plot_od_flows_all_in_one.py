#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_od_flows_all_in_one.py

ステップ３の成果（起点→ホールの flow）を読み込んで、
Folium で OD フローを地図上に可視化し、
HTML ファイルに一気に出力するスクリプト
"""
import os
import pandas as pd
import folium

# ─── 設定セクション ─────────────────────────
INPUT_FILE   = "huff_step3_all_in_one.xlsx"  # ステップ３成果ファイル
SHEET_NAME   = "flows_detail"                # 起点→ホールの詳細データ
OUTPUT_HTML  = "od_flow_map_all_in_one.html" # 出力する HTML

# ─── 1. データ読み込み ───────────────────────
print(f"Loading {INPUT_FILE} → sheet: {SHEET_NAME} …")
df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

# ─── 2. 必要列チェック ───────────────────────
required_cols = {"origin_lat", "origin_lon", "shop_lat", "shop_lon", "flow"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"必要な列が見つかりません: {missing}")

# ─── 3. 欠損値除外 ─────────────────────────
df_valid = df.dropna(subset=["origin_lat", "origin_lon", "shop_lat", "shop_lon", "flow"])
print(f"Valid flows: {len(df_valid)} 件")

# ─── 4. Folium 地図の初期化 ─────────────────
# 中心座標は起点の平均座標
center_lat = df_valid["origin_lat"].mean()
center_lon = df_valid["origin_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

# ─── 5. OD フローを線で描画 ─────────────────
max_flow = df_valid["flow"].max()
for _, row in df_valid.iterrows():
    origin = [row["origin_lat"], row["origin_lon"]]
    dest   = [row["shop_lat"],    row["shop_lon"]]
    # 線の太さを flow に応じて調整
    weight = (row["flow"] / max_flow) * 8 + 1
    folium.PolyLine(
        locations=[origin, dest],
        weight=weight,
        color="#3388ff",
        opacity=0.5,
        tooltip=(
            f"Origin {int(row['origin_id'])} → {row['store']}<br>"
            f"Flow: {row['flow']:.1f}"
        )
    ).add_to(m)

# ─── 6. HTML に保存 ─────────────────────────
print("出力先ディレクトリ:", os.getcwd())
m.save(OUTPUT_HTML)
print(f"\n完了：{OUTPUT_HTML} を出力しました。{len(df_valid)} 件のフローをマッピングしました。")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_flow_lines.py

ステップ3の成果を使って、
各起点→店舗 の期待来店者数フローを
Folium の FeatureGroup（店舗ごと）で可視化します。

「レイヤーコントロール」から店舗をONにすると、
その店舗に来る各起点からの線が引かれ、
線の太さは期待来店者数に比例します。
"""

import math
import pandas as pd
import folium
from folium import FeatureGroup, LayerControl

# ───── 設定 ─────
INPUT_FILE  = "huff_step3_all_in_one.xlsx"
SHEET_NAME  = "flows_detail"   # origin_id, origin_lat, origin_lon, shop_lat, shop_lon, store, flow が入ったシート
OUTPUT_HTML = "flow_lines_map.html"

def main():
    # 1) データ読み込み
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # 必要列のチェック
    required = {"origin_id","origin_lat","origin_lon","shop_lat","shop_lon","store","flow"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"不足列: {missing}")

    # 欠損除外
    df = df.dropna(subset=["origin_lat","origin_lon","shop_lat","shop_lon","flow"])

    # 2) 地図の中心を起点の平均位置に
    center_lat = df["origin_lat"].mean()
    center_lon = df["origin_lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # 3) 各店舗ごとに FeatureGroup を作成し，線を追加
    for store, grp in df.groupby("store"):
        fg = FeatureGroup(name=store, show=False)
        for _, row in grp.iterrows():
            # 線の太さを flow に比例させる（お好みでスケーリング係数を調整）
            weight = max(1, math.sqrt(row["flow"]) / 5)
            folium.PolyLine(
                locations=[
                    (row["origin_lat"], row["origin_lon"]),
                    (row["shop_lat"],   row["shop_lon"])
                ],
                color="blue",
                weight=weight,
                opacity=0.6,
                tooltip=(
                    f"起点ID: {int(row['origin_id'])}<br>"
                    f"流入予測: {row['flow']:.0f} 人"
                )
            ).add_to(fg)
        fg.add_to(m)

    # 4) 店舗の位置をマーカーで追加
    #    （店舗ごとに緯度経度の平均をとってマーカーを置く）
    stores_pos = (
        df.groupby("store")[["shop_lat","shop_lon"]]
          .mean()
          .reset_index()
    )
    for _, row in stores_pos.iterrows():
        folium.Marker(
            location=[row["shop_lat"], row["shop_lon"]],
            popup=row["store"],
            icon=folium.Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)

    # 5) レイヤーコントロール
    LayerControl(collapsed=False, position="topright").add_to(m)

    # 6) 出力
    m.save(OUTPUT_HTML)
    print(f"完了: {OUTPUT_HTML} を出力しました。")

if __name__ == "__main__":
    main()

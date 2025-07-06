#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_flows_by_store_layers.py

各起点→店舗の期待来店者数(flow)を、
店舗ごとにレイヤー分けしたポリラインで可視化します。
チェックボックスで任意の店舗のみ表示できます。
"""

import pandas as pd
import folium
from folium import FeatureGroup, LayerControl, PolyLine, Marker, Icon

# ───── 設定 ─────
INPUT_FILE  = "huff_step3_all_in_one.xlsx"
SHEET_NAME  = "flows_detail"       # origin_id, origin_lat, origin_lon, shop_lat, shop_lon, flow が入ったシート
OUTPUT_HTML = "flows_per_store_map.html"

def main():
    # 1) データ読み込み
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    # 必要列チェック
    for col in ["origin_lat","origin_lon","shop_lat","shop_lon","store","flow"]:
        if col not in df.columns:
            raise ValueError(f"列 {col} がありません")

    # 2) 地図の中心を計算
    center = [ df["origin_lat"].mean(), df["origin_lon"].mean() ]
    m = folium.Map(location=center, zoom_start=12)

    # 3) 店舗マーカーをプロット
    shop_pos = (
        df.groupby("store")[["shop_lat","shop_lon"]]
          .mean()
          .reset_index()
    )
    for _, row in shop_pos.iterrows():
        Marker(
            location=[row["shop_lat"], row["shop_lon"]],
            popup=row["store"],
            icon=Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)

    # 4) 線の太さスケール用
    max_flow = df["flow"].max()

    # 5) 店舗ごとにFlowレイヤーを作成
    for store, grp in df.groupby("store"):
        fg = FeatureGroup(name=f"{store} ⇒ flows", show=False)
        for _, r in grp.iterrows():
            # 起点→店舗を結ぶポリライン
            PolyLine(
                locations=[
                    [r["origin_lat"], r["origin_lon"]],
                    [r["shop_lat"],   r["shop_lon"]]
                ],
                color="blue",
                weight=1 + (r["flow"]/max_flow)*8,  # 太さ1～9
                opacity=0.5
            ).add_to(fg)
        fg.add_to(m)

    # 6) レイヤーコントロールを追加
    LayerControl(collapsed=False, position="topright").add_to(m)

    # 7) 地図を保存
    m.save(OUTPUT_HTML)
    print(f"完了: {OUTPUT_HTML} を出力しました")

if __name__ == "__main__":
    main()

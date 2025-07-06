#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_catchment_map.py

Huffモデル ステップ3の全結果ファイルから
キャッチメント（各起点が最も選択した店舗）を
Folium 地図上にレイヤー分けして可視化します。
"""

import pandas as pd
import folium
import itertools
from folium import FeatureGroup, LayerControl

# ───── 設定 ─────
INPUT_FILE   = "huff_step3_all_in_one.xlsx"
SHEET_DETAIL = "flows_detail"   # origin_id, origin_lat, origin_lon, shop_lat, shop_lon, store, P_ij, flow ...
OUTPUT_HTML  = "catchment_map.html"

def main():
    # 1) ステップ3詳細読み込み
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_DETAIL)

    # 必要な列が揃っているか最低限チェック
    req = {"origin_id","origin_lat","origin_lon","shop_lat","shop_lon","store","P_ij","flow"}
    missing = req - set(df.columns)
    if missing:
        raise ValueError(f"入力シートに不足列があります: {missing}")

    # 緯度経度漏れ行は除外
    df = df.dropna(subset=["origin_lat","origin_lon","shop_lat","shop_lon"])

    # 2) 各起点ごとにP_ij最大の店舗（キャッチメント）を抽出
    df["rank"] = df.groupby("origin_id")["P_ij"] \
                   .rank(method="first", ascending=False)
    df_catch = df[df["rank"] == 1].copy()

    # 3) 店舗の代表位置を算出（平均でもOK）
    stores_pos = (
        df.groupby("store")[["shop_lat","shop_lon"]]
          .mean()
          .reset_index()
    )

    # 4) カラーパレット作成
    store_list = df_catch["store"].unique()
    color_cycle = itertools.cycle([
        "blue","green","red","purple","orange","darkred",
        "lightred","beige","darkblue","darkgreen","cadetblue","darkpurple"
    ])
    palette = {st: next(color_cycle) for st in store_list}

    # 5) 地図を起点の中心に生成
    center_lat = df_catch["origin_lat"].mean()
    center_lon = df_catch["origin_lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # 6) キャッチメント起点を店舗ごとにレイヤー化
    for st, grp in df_catch.groupby("store"):
        fg = FeatureGroup(name=f"{st}", show=False)
        for _, row in grp.iterrows():
            folium.CircleMarker(
                location=[row["origin_lat"], row["origin_lon"]],
                radius=4,
                color=palette[st],
                fill=True,
                fill_color=palette[st],
                fill_opacity=0.6,
                weight=0,
                popup=(
                    f"<b>{st}</b><br>"
                    f"P_ij = {row['P_ij']:.3f}<br>"
                    f"flow = {row['flow']:.1f}"
                )
            ).add_to(fg)
        fg.add_to(m)

    # 7) 店舗位置をアイコンマーカーで表示
    for _, row in stores_pos.iterrows():
        folium.Marker(
            location=[row["shop_lat"], row["shop_lon"]],
            popup=row["store"],
            icon=folium.Icon(color="black", icon="home", prefix="fa")
        ).add_to(m)

    # 8) レイヤーコントロール
    LayerControl(collapsed=False).add_to(m)

    # 9) HTML 出力
    m.save(OUTPUT_HTML)
    print(f"完了: {OUTPUT_HTML} を出力しました。")

if __name__ == "__main__":
    main()

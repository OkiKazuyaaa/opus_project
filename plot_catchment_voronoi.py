#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_catchment_voronoi.py

Huffモデルの P_ij を使って、
“各起点が最も選ぶ店舗” を色分け表示するキャッチメントマップ。
"""

import pandas as pd
import folium
import branca.colormap as cm

# ───── 設定 ─────
INPUT_FILE  = "huff_step3_all_in_one.xlsx"
SHEET_NAME  = "flows_detail"  # origin_id, origin_lat, origin_lon, store, P_ij があるシート
OUTPUT_HTML = "catchment_map.html"

def main():
    # 1) データ読み込み
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # 必要列チェック
    for col in ["origin_lat","origin_lon","store","P_ij"]:
        if col not in df.columns:
            raise ValueError(f"列 {col} がありません")

    # 2) 各起点ごとに「最もP_ijが高いstore」を選択
    #    (= groupby origin_id → idxmax)
    idx = df.groupby("origin_id")["P_ij"].idxmax()
    catch_df = df.loc[idx, ["origin_id","origin_lat","origin_lon","store","P_ij"]]

    # 3) 色のスケール準備: 店舗数分のカラーリストを生成
    stores = sorted(catch_df["store"].unique())
    colormap = cm.linear.Set1_09.scale(0, len(stores))
    color_dict = {s: colormap(i) for i,s in enumerate(stores)}

    # 4) 地図の初期化：全起点の中心あたりで
    center = [catch_df["origin_lat"].mean(), catch_df["origin_lon"].mean()]
    m = folium.Map(location=center, zoom_start=12)

    # 5) GeoJSONレイヤーに起点を追加
    for store in stores:
        grp = catch_df[catch_df["store"] == store]
        fg = folium.FeatureGroup(name=store, show=False)
        for _, row in grp.iterrows():
            folium.CircleMarker(
                location=[row["origin_lat"], row["origin_lon"]],
                radius=4,
                color=None,
                fill=True,
                fill_color=color_dict[store],
                fill_opacity=0.6,
                tooltip=f"起点ID:{int(row['origin_id'])}<br>店舗:{store}<br>P_ij:{row['P_ij']:.3f}"
            ).add_to(fg)
        fg.add_to(m)

    # 6) 店舗アイコンをプロット
    #    (店舗の緯度経度は flows_detail から平均を取っておく)
    shop_pos = (
        df.groupby("store")[["shop_lat","shop_lon"]]
          .mean()
          .reset_index()
    )
    for _, r in shop_pos.iterrows():
        folium.Marker(
            [r["shop_lat"], r["shop_lon"]],
            icon=folium.Icon(color="red", icon="home", prefix="fa"),
            popup=r["store"]
        ).add_to(m)

    # 7) カラーバーとレイヤーコントロール
    colormap.caption = "店舗別キャッチメント色"
    m.add_child(colormap)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # 8) 保存
    m.save(OUTPUT_HTML)
    print(f"完了: {OUTPUT_HTML} を出力しました")

if __name__ == "__main__":
    main()

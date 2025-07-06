#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catchment_area_map.py

Huffモデルのステップ３成果（Pᵢⱼ）を読み込み、
各起点(origin)ごとにPᵢⱼが最大となる店舗を
色分けして Folium マップ上にプロットし、
さらに各店舗の位置もマーカーで表示するスクリプト。
"""

import pandas as pd
import folium
from sklearn.preprocessing import LabelEncoder
import matplotlib.cm as cm
import matplotlib.colors as colors

# ─── 設定 ───
INPUT_FILE   = "huff_step3_all_in_one.xlsx"  # ステップ3成果ファイル
INPUT_SHEET  = "flows_detail"                # 起点ごとのPᵢⱼが載っているシート名
OUTPUT_HTML  = "catchment_area_map.html"     # 出力HTML

# 1) データ読み込み
df = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)

# 2) 必要列チェック
required = {"origin_id","origin_lat","origin_lon","store","shop_lat","shop_lon","P_ij"}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"ステップ３成果ファイルに不足している列: {missing}")

# 3) origin_idごとにP_ij最大の店舗を選択
idx_max = df.groupby("origin_id")["P_ij"].idxmax()
df_best = df.loc[idx_max].reset_index(drop=True)

# 4) 店舗ごとに色を割り当て
stores = df_best["store"].unique()
le = LabelEncoder().fit(stores)
n_stores = len(stores)
cmap = cm.get_cmap("tab20", n_stores)
norm = colors.Normalize(vmin=0, vmax=n_stores-1)
store_colors = {
    store: colors.to_hex(cmap(norm(i)))
    for i, store in enumerate(le.classes_)
}

# 5) Foliumマップ初期化（中心は起点の平均座標）
center_lat = float(df_best["origin_lat"].mean())
center_lon = float(df_best["origin_lon"].mean())
m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

# 6) 各起点に円マーカーを追加（色＝割り当て店舗）
for _, row in df_best.iterrows():
    folium.CircleMarker(
        location=[row["origin_lat"], row["origin_lon"]],
        radius=6,
        color=store_colors[row["store"]],
        fill=True,
        fill_color=store_colors[row["store"]],
        fill_opacity=0.7,
        weight=0,
        popup=folium.Popup(f"起点ID: {row['origin_id']}<br>店舗: {row['store']}", max_width=200)
    ).add_to(m)

# 7) 店舗位置にマーカーを追加
df_stores = df_best[["store","shop_lat","shop_lon"]].drop_duplicates("store")
for _, row in df_stores.iterrows():
    folium.Marker(
        location=[row["shop_lat"], row["shop_lon"]],
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
        popup=row["store"]
    ).add_to(m)

# 8) 凡例を埋め込み（HTML用）
legend_html = """
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; 
    width: 200px; height: auto; 
    background: white; 
    border:2px solid grey; 
    padding: 10px;
    font-size:12px;
    z-index:9999;
">
<b>キャッチメントエリアの店舗</b><br>
"""
for store, col in store_colors.items():
    legend_html += f"""<i style="
        background:{col};
        width:12px; height:12px; 
        display:inline-block;
        margin-right:6px;
        "></i>{store}<br>"""
legend_html += "</div>"

m.get_root().html.add_child(folium.Element(legend_html))

# 9) ファイル出力
m.save(OUTPUT_HTML)
print(f"▶ 完了: {OUTPUT_HTML} を出力しました。")

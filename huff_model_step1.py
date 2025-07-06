#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
huff_model_step1.py

ステップ①: Huffモデルの
- 魅力度関数 A_i の計算
- 起点距離データの作成
を行うサンプルコード

前提: shops.xlsx に以下の列を含む
  - 店舗名, 緯度, 経度, P台数, S台数
"""
import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

# パラメータ設定
ALPHA = 1.0  # 台数の重み
BETA  = 2.0  # 距離の重み

# ハバースイン距離関数
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半径(m)
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return 2*R*atan2(sqrt(a), sqrt(1-a))

# 1) 店舗データ読み込み
df_stores = pd.read_excel('miyazaki_5pachi_cached.xlsx')  # 緯度, 経度, P台数, S台数

# 2) 起点を格子点で生成 (例: bounding box を 10x10 グリッドで)
lat_min, lat_max = df_stores['緯度'].min(), df_stores['緯度'].max()
lon_min, lon_max = df_stores['経度'].min(), df_stores['経度'].max()
num_grid = 10  # 10x10
lats = np.linspace(lat_min, lat_max, num_grid)
lons = np.linspace(lon_min, lon_max, num_grid)
origins = [(lat, lon) for lat in lats for lon in lons]

# 3) 距離行列と魅力度行列の作成
results = []
for j, (olat, olon) in enumerate(origins):
    # 各店舗への距離・魅力度を計算
    dists = []
    A_vals = []
    for _, row in df_stores.iterrows():
        dist = haversine(olat, olon, row['緯度'], row['経度']) + 1e-6  # ゼロ除算回避
        size = (row['P台数'] + row['S台数'])
        A = (size ** ALPHA) / (dist ** BETA)
        dists.append(dist)
        A_vals.append(A)
    # 選択確率 P_ij
    total_A = sum(A_vals)
    P_ij = [A / total_A for A in A_vals]

    # 登録
    for i, row in df_stores.iterrows():
        results.append({
            'origin_id': j,
            'origin_lat': olat,
            'origin_lon': olon,
            'store': row['ホール名'],
            'dist_m': dists[i],
            'A_i': A_vals[i],
            'P_ij': P_ij[i]
        })

# 4) DataFrame にまとめ
df_results = pd.DataFrame(results)

# 5) 出力
df_results.to_excel('huff_step1_results.xlsx', index=False)
print('完了: huff_step1_results.xlsx を出力しました')

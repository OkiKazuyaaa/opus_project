#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import pandas as pd

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
# １）ホールデータ（緯度・経度・P台数・S台数入り Excel）
STORE_FILE     = "miyazaki_5pachi_geocode.xlsx"
STORE_SHEET    = "Sheet1"

# ２）地域データ（地域ごとのID・緯度・経度・人口入り Excel）
REGION_FILE    = "market_data.xlsx"
REGION_SHEET   = "地域データ"

# 出力ファイル
OUTPUT_FILE    = "huff_step3_all_in_one.xlsx"

# Huff モデルのパラメータ
ALPHA = 1.0   # 魅力度の重み
BETA  = 2.0   # 距離減衰の重み

# ──────────────────────────────────────────────
# ハバーサイン距離（メートル）
# ──────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半径 (m)
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ    = math.radians(lat2 - lat1)
    Δλ    = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ──────────────────────────────────────────────
# １．データ読み込み
# ──────────────────────────────────────────────
print("Step1: ホールデータ読み込み →", STORE_FILE, STORE_SHEET)
df_stores = pd.read_excel(STORE_FILE, sheet_name=STORE_SHEET)
for c in ("緯度","経度","P台数","S台数"):
    if c not in df_stores.columns:
        raise KeyError(f"ホールデータに列「{c}」がありません。")

print("Step1: 地域データ読み込み →", REGION_FILE, REGION_SHEET)
df_region = pd.read_excel(REGION_FILE, sheet_name=REGION_SHEET)
for c in ("地域ID","緯度","経度","人口"):
    if c not in df_region.columns:
        raise KeyError(f"地域データに列「{c}」がありません。")

# ──────────────────────────────────────────────
# ２．Huffモデル計算：A_i, P_ij, flow
# ──────────────────────────────────────────────
print("Step2: Huffモデル計算中…")
records = []
# まず各 origin について分母 Σ_j A_j / d_ij^β を計算しておく
for _, origin in df_region.iterrows():
    oid    = origin["地域ID"]
    olat   = origin["緯度"]
    olon   = origin["経度"]
    pop    = origin["人口"]
    # 魅力度 A_i = (P+S)^α
    # 距離減衰要素 S_j = A_j / (d_ij^β)
    Sj_list = []
    for _, shop in df_stores.iterrows():
        size = shop["P台数"] + shop["S台数"]
        Ai   = size ** ALPHA
        d    = haversine(olat, olon, shop["緯度"], shop["経度"]) + 1e-6
        Sj   = Ai / (d ** BETA)
        Sj_list.append(Sj)
    denom = sum(Sj_list)

    # 各店舗ごと P_ij, flow を記録
    for (Sj, (_, shop)) in zip(Sj_list, df_stores.iterrows()):
        pij  = Sj / denom if denom > 0 else 0.0
        flow = pij * pop
        records.append({
            "origin_id":        oid,
            "origin_lat":       olat,
            "origin_lon":       olon,
            "population":       pop,
            "store":            shop["ホール名"],
            "shop_lat":         shop["緯度"],
            "shop_lon":         shop["経度"],
            "P台数":            shop["P台数"],
            "S台数":            shop["S台数"],
            "A_i":              (shop["P台数"]+shop["S台数"])**ALPHA,
            "distance_m":       haversine(olat, olon, shop["緯度"], shop["経度"]),
            "P_ij":             pij,
            "flow":             flow
        })

df_detail = pd.DataFrame(records)

# ──────────────────────────────────────────────
# ３．店舗ごとの総 flow を集計
# ──────────────────────────────────────────────
print("Step3: 店舗別期待来店人口を集計中…")
df_store = (
    df_detail
    .groupby("store", as_index=False)["flow"]
    .sum()
    .rename(columns={"flow":"expected_visitors"})
)

# ──────────────────────────────────────────────
# ４．結果を Excel に書き出し
# ──────────────────────────────────────────────
print("Step4: 出力 →", OUTPUT_FILE)
with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    df_detail.to_excel(writer, sheet_name="flows_detail", index=False)
    df_store.to_excel(writer, sheet_name="flows_by_store", index=False)

print("完了！", OUTPUT_FILE, "を出力しました。")

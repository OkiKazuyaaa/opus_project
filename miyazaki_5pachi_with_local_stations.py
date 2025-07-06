#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
miyazaki_5pachi_with_local_stations.py

5pachi.com 宮崎県ページをスクレイピングし、
住所→緯度経度→ローカルキャッシュ済み駅リストで
最寄駅直線距離を BallTree（ハバースイン距離）を用いて高速に取得し、
Excel に出力します。

事前準備:
  1. fetch_stations.py を実行し miyazaki_stations.json を生成
  2. 必要ライブラリをインストール
     pip install requests pandas beautifulsoup4 geopy scikit-learn openpyxl
"""
import time
import re
import json
import requests
import pandas as pd
import shelve
import numpy as np
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from sklearn.neighbors import BallTree

# ───── 設定 ─────
BASE_URL     = "https://5pachi.com/pref/miyazaki"
OUTPUT_XLSX  = "miyazaki_5pachi_with_local_stations.xlsx"
HEADERS      = {"User-Agent": "Mozilla/5.0"}

# geopy 初期化
geolocator  = Nominatim(user_agent="5pachi_local", timeout=20)

# ジオコーディングキャッシュ
geo_cache    = shelve.open("geo_cache.db")

# ───── ヘルパー ─────
def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def get_total_and_pages(soup: BeautifulSoup):
    txt = soup.find(string=re.compile(r"該当件数は、\s*\d+\s*件"))
    total = int(re.search(r"(\d+)", txt).group(1)) if txt else 0
    pages = 1
    pg = soup.find("ul", class_=re.compile("pagination"))
    if pg:
        nums = [int(a.get_text()) for a in pg.find_all("a") if a.get_text().isdigit()]
        if nums:
            pages = max(nums)
    return total, pages

def parse_rows(soup: BeautifulSoup):
    tbl = soup.find("table")
    return tbl.find_all("tr")[1:] if tbl else []

def geocode_cached(addr: str):
    # キャッシュキーは「フル文字列」のみ
    if addr in geo_cache:
        return geo_cache[addr]

    loc = None
    try:
        # まずはフル住所をそのまま渡す
        loc = geolocator.geocode(addr + ", 日本", language="ja")
    except Exception:
        pass

    if not loc:
        # どうしてもフル住所でヒットしない場合のみ
        short = normalize_address(addr)  # 「…丁目…番」まで含めた短縮
        try:
            loc = geolocator.geocode(short + ", 日本", language="ja")
        except Exception:
            pass

    # 結果をキャッシュ
    result = (loc.latitude, loc.longitude) if loc else (None, None)
    geo_cache[addr] = result
    geo_cache.sync()
    time.sleep(1)
    return result


# ───── メイン処理 ─────
def main():
    # --- 店舗情報スクレイピング ---
    soup0 = get_soup(BASE_URL)
    total, pages = get_total_and_pages(soup0)
    print(f"該当件数: {total} 件 → {pages} ページ")

    shops = []
    for i in range(1, pages+1):
        url = BASE_URL if i==1 else f"{BASE_URL}?page={i}"
        print(f"▶ ページ取得: {url}")
        soup = get_soup(url)
        rows = parse_rows(soup)
        print(f"  行数: {len(rows)} 件")
        for tr in rows:
            cols = tr.find_all("td")
            shops.append({
                "日付":   cols[0].get_text(strip=True),
                "ホール名": cols[2].get_text(strip=True),
                "住所":   cols[3].get_text(strip=True),
                "P台数": cols[4].get_text(strip=True),
                "S台数": cols[5].get_text(strip=True)
            })
        time.sleep(1)
    print(f"★ 合計取得件数: {len(shops)} 件")

    # --- 緯度経度取得 ---
    lat_list, lon_list = [], []
    for shop in shops:
        addr = shop["住所"]
        lat, lon = geocode_cached(addr)
        shop["緯度"], shop["経度"] = lat, lon
        if lat is not None and lon is not None:
            lat_list.append(lat)
            lon_list.append(lon)

    # --- 事前に駅リスト読み込み & フィルタリング ---
    print("駅リスト読み込み…")
    with open("miyazaki_stations.json", encoding="utf-8") as fp:
        stations = json.load(fp)
    # ショップ座標範囲に少しマージンを加えてフィルタ
    if lat_list and lon_list:
        lat_min, lat_max = min(lat_list)-0.1, max(lat_list)+0.1
        lon_min, lon_max = min(lon_list)-0.1, max(lon_list)+0.1
        stations = [s for s in stations
                    if lat_min <= s.get("lat",0) <= lat_max
                    and lon_min <= s.get("lon",0) <= lon_max]
    print(f"→ フィルタ後の駅リスト件数: {len(stations)} 件")

    # BallTree 構築
    coords_rad = np.radians([[s["lat"], s["lon"]] for s in stations])
    names = [s["name"] for s in stations]
    tree = BallTree(coords_rad, metric='haversine')

    # --- 最寄駅検索 ---
    for shop in shops:
        lat, lon = shop.get("緯度"), shop.get("経度")
        if lat is not None and lon is not None:
            rad_pt = np.radians([[lat, lon]])
            dist_rad, ind = tree.query(rad_pt, k=1)
            dist_m = float(dist_rad[0][0]) * 6371000
            idx = int(ind[0][0])
            shop["最寄駅"] = names[idx]
            shop["駅まで直線距離(m)"] = round(dist_m, 1)
        else:
            shop["最寄駅"] = ""
            shop["駅まで直線距離(m)"] = ""

    geo_cache.close()

    # --- Excel 出力 ---
    df = pd.DataFrame(
        shops,
        columns=[
            "日付","ホール名","住所","緯度","経度",
            "最寄駅","駅まで直線距離(m)","P台数","S台数"
        ]
    )
    df.to_excel(OUTPUT_XLSX, index=False)
    print(f"\n完了: {OUTPUT_XLSX} を出力しました。店舗数: {len(shops)} 件")

if __name__ == "__main__":
    main()

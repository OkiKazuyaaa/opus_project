#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pworld_pc_selenium_scraper.py

5pachi.com 宮崎県ページをスクレイピングし、
住所→緯度経度→最寄駅直線距離を
ローカルキャッシュ付きで取得し Excel に出力
"""

import re
import time
import shelve
import requests
import pandas as pd
import overpy
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# ───── 設定 ─────
BASE_URL    = "https://5pachi.com/pref/miyazaki"
OUTPUT_XLSX = "miyazaki_5pachi_cached.xlsx"
HEADERS     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# geopy と Overpass 初期化
geolocator   = Nominatim(user_agent="5pachi_cached", timeout=20)
osm_api      = overpy.Overpass()

# キャッシュ用 shelve
geo_cache     = shelve.open("geo_cache.db")
station_cache = shelve.open("station_cache.db")

# ───── ヘルパー ─────
def normalize_address(addr: str) -> str:
    """住所文字列を番地まで含めて正規化"""
    s = addr.replace("　"," ").strip()
    # 「市」「町」「村」＋「丁目〇番」をできるだけ拾う
    m = re.match(r"(.*?[都道府県].*?[市町村].*?\d+丁目\d+番)", s)
    return m.group(1) if m else s

def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def get_total_hits_and_pages(soup: BeautifulSoup):
    # 「該当件数は、92件です」などから件数を抜き出し
    txt = soup.find(string=re.compile(r"該当件数は、\s*\d+\s*件"))
    total = int(re.search(r"(\d+)", txt).group(1)) if txt else 0
    # ページ数は pagination リンクから拾う
    pages = 1
    pg = soup.find('ul', class_=re.compile('pagination'))
    if pg:
        nums = [int(a.get_text()) for a in pg.find_all('a') if a.get_text().isdigit()]
        pages = max(nums) if nums else 1
    return total, pages

def parse_rows(soup: BeautifulSoup):
    tbl = soup.find("table")
    if not tbl:
        return []
    return tbl.find_all("tr")[1:]  # header を飛ばしてデータ行だけ

def geocode_cached(addr: str):
    """ジオコーディングをキャッシュ付きで実行"""
    if addr in geo_cache:
        return geo_cache[addr]
    loc = None
    try:
        loc = geolocator.geocode(f"{addr}, 日本", language="ja")
    except:
        pass
    if not loc:
        short = normalize_address(addr)
        try:
            loc = geolocator.geocode(f"{short}, 日本", language="ja")
        except:
            pass
    res = (loc.latitude, loc.longitude) if loc else (None, None)
    geo_cache[addr] = res
    geo_cache.sync()
    time.sleep(1)  # Nominatim 利用規約に鑑み少し待機
    return res

def find_nearest_cached(lat: float, lon: float):
    """
    Overpass で最寄り駅をキャッシュ付きで検索。
    半径を小→大とステップアップしてタグを追加。
    """
    key = f"{lat:.6f},{lon:.6f}"
    if key in station_cache:
        return station_cache[key]

    tag_filters = [
        'node(around:{r},{lat},{lon})[railway=station]',
        'node(around:{r},{lat},{lon})[railway=halt]',
        'node(around:{r},{lat},{lon})[railway=tram_stop]',
        'node(around:{r},{lat},{lon})[public_transport=stop_position]',
        'way(around:{r},{lat},{lon})[railway=station]',
        'rel(around:{r},{lat},{lon})[railway=station]',
    ]
    # 試す半径 (m) を小→大
    for radius in (2000, 5000, 10000, 30000):
        parts = [filt.format(r=radius, lat=lat, lon=lon) for filt in tag_filters]
        q = "(\n  " + ";\n  ".join(parts) + ";\n);\nout center tags;"
        try:
            res = osm_api.query(q)
        except Exception:
            continue

        candidates = []
        for n in res.nodes:
            name = n.tags.get('name')
            if name:
                d = geodesic((lat,lon),(n.lat,n.lon)).meters
                candidates.append((d, name))
        for w in res.ways:
            if w.center_lat and w.center_lon:
                name = w.tags.get('name')
                d = geodesic((lat,lon),(w.center_lat,w.center_lon)).meters
                candidates.append((d, name))
        for r in res.relations:
            if r.center_lat and r.center_lon:
                name = r.tags.get('name')
                d = geodesic((lat,lon),(r.center_lat,r.center_lon)).meters
                candidates.append((d, name))

        if candidates:
            d, name = min(candidates, key=lambda x: x[0])
            out = (name, round(d,1))
            station_cache[key] = out
            station_cache.sync()
            time.sleep(1)
            return out

    # どの範囲でも見つからなかった
    station_cache[key] = (None, None)
    station_cache.sync()
    return (None, None)

def main():
    # 1ページ目で件数とページ数を取得
    soup0 = get_soup(BASE_URL)
    total, pages = get_total_hits_and_pages(soup0)
    print(f"該当件数: {total} 件 → {pages} ページ")

    # 全ページ URL を組み立て
    urls = [BASE_URL if i==1 else f"{BASE_URL}?page={i}"
            for i in range(1, pages+1)]

    shops = []
    for url in urls:
        print(f"▶ ページ取得: {url}")
        soup = get_soup(url)
        rows = parse_rows(soup)
        print(f"  行数: {len(rows)} 件")
        for tr in rows:
            cols = tr.find_all("td")
            shops.append({
                '日付':   cols[0].get_text(strip=True),
                'ホール名': cols[2].get_text(strip=True),
                '住所':   cols[3].get_text(strip=True),
                'P台数': cols[4].get_text(strip=True),
                'S台数': cols[5].get_text(strip=True),
            })
        time.sleep(1)

    print(f"★ 合計取得件数: {len(shops)} 件")

    # 各店舗ごとにジオコーディング→最寄駅検索
    for shop in shops:
        addr = shop['住所']
        lat, lon = geocode_cached(addr)
        shop['緯度'], shop['経度'] = lat, lon
        if lat and lon:
            station, dist = find_nearest_cached(lat, lon)
            shop['最寄駅']               = station or ''
            shop['駅まで直線距離(m)']   = dist    or ''
        else:
            shop['最寄駅']               = ''
            shop['駅まで直線距離(m)']   = ''

    geo_cache.close()
    station_cache.close()

    # DataFrame 化して Excel 出力
    df = pd.DataFrame(shops, columns=[
        '日付','ホール名','住所','緯度','経度',
        '最寄駅','駅まで直線距離(m)','P台数','S台数'
    ])
    df.to_excel(OUTPUT_XLSX, index=False)
    print(f"\n完了: {OUTPUT_XLSX} を出力しました。店舗数: {len(shops)} 件")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
miyazaki_5pachi_geocode_fallback.py

5pachi.com 宮崎県ページをスクレイピングし、
住所→緯度経度を Nominatim→ArcGIS の順で取得、
ローカルキャッシュ付きで Excel に出力するスクリプト
"""

import time
import re
import requests
import pandas as pd
import shelve
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim, ArcGIS

# ───── 設定 ─────
BASE_URL    = "https://5pachi.com/pref/miyazaki"
OUTPUT_XLSX = "miyazaki_5pachi_geocode.xlsx"
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# geocoder 初期化
nominatim = Nominatim(user_agent="5pachi_geocode", timeout=10)
arcgis    = ArcGIS(timeout=10)

# キャッシュ用 shelve
cache = shelve.open("geo_cache_fallback.db")

def normalize(addr: str) -> str:
    """
    住所の余計な全角/半角スペースを詰め、
    「町」「丁目」の前後にスペースを入れるなどの軽い正規化。
    """
    s = addr.replace("　", " ").strip()
    # 「○丁目」「○番」「○号」の直前にスペース
    s = re.sub(r"(\d+)(丁目|番地|番|号)", r"\1 \2", s)
    return s

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
        nums = [int(a.text) for a in pg.find_all("a") if a.text.isdigit()]
        pages = max(nums) if nums else 1
    return total, pages

def parse_rows(soup: BeautifulSoup):
    tbl = soup.find("table")
    if not tbl:
        return []
    return tbl.find_all("tr")[1:]

def geocode(addr: str):
    """Nominatim→ArcGIS の順で geocode。"""
    key = addr
    if key in cache:
        return cache[key]

    lat = lon = None

    # 1) Nominatim
    try:
        loc = nominatim.geocode(addr + ", 日本", language="ja")
        if loc:
            lat, lon = loc.latitude, loc.longitude
    except Exception:
        pass

    # 2) ArcGIS (Nominatim が取れなかった場合のみ)
    if lat is None or lon is None:
        try:
            loc2 = arcgis.geocode(addr)
            if loc2:
                lat, lon = loc2.latitude, loc2.longitude
        except Exception:
            pass

    cache[key] = (lat, lon)
    cache.sync()
    # サーバー側レートリミット回避
    time.sleep(1)
    return lat, lon

def main():
    # 1) ページ数取得
    soup0 = get_soup(BASE_URL)
    total, pages = get_total_and_pages(soup0)
    print(f"該当件数: {total} 件 → {pages} ページ")

    # 2) 全ページスクレイピング
    shops = []
    for p in range(1, pages+1):
        url = BASE_URL if p == 1 else f"{BASE_URL}?page={p}"
        print(f"▶ ページ取得: {url}")
        soup = get_soup(url)
        rows = parse_rows(soup)
        print(f"  行数: {len(rows)} 件")
        for tr in rows:
            cols = tr.find_all("td")
            shops.append({
                "日付":    cols[0].get_text(strip=True),
                "ホール名":cols[2].get_text(strip=True),
                "住所_raw":cols[3].get_text(strip=True),
                "P台数":  cols[4].get_text(strip=True),
                "S台数":  cols[5].get_text(strip=True),
            })
        time.sleep(1)

    print(f"★ 合計取得件数: {len(shops)} 件")

    # 3) 各住所を正規化→ジオコーディング
    for shop in shops:
        addr0 = shop["住所_raw"]
        addr = normalize(addr0)
        lat, lon = geocode(addr)
        shop["緯度"] = lat if lat else ""
        shop["経度"] = lon if lon else ""
        if not lat:
            print(f"⚠️ Geocode NG → {addr0}")

    cache.close()

    # 4) DataFrame & Excel 出力
    df = pd.DataFrame(shops, columns=[
        "日付","ホール名","住所_raw","緯度","経度","P台数","S台数"
    ])
    df.rename(columns={"住所_raw":"住所"}, inplace=True)
    df.to_excel(OUTPUT_XLSX, index=False)
    print(f"\n完了: {OUTPUT_XLSX} を出力しました。")

if __name__ == "__main__":
    main()

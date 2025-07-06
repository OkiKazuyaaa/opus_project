#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_stations.py

Overpass API から宮崎県内の全駅ノードを取得し、
JSON ファイルにキャッシュ保存するスクリプト。
緯度・経度を float にキャストして JSON シリアライズ可能にしています。
"""

import json
import overpy
import sys

def fetch_all_stations(output_path="miyazaki_stations.json"):
    print("Overpass に問い合わせ中…")
    api = overpy.Overpass()

    # 宮崎県の大まかなバウンディングボックス
    # (min_lat, min_lon, max_lat, max_lon)
    bbox = (31.4, 130.7, 32.9, 131.9)

    # 駅タグの node・way・relation をまとめて取得
    query = f"""
    (
      node["railway"="station"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["railway"="station"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      rel["railway"="station"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out center tags;
    """
    try:
        result = api.query(query)
    except Exception as e:
        print("Overpass API エラー:", e, file=sys.stderr)
        sys.exit(1)

    stations = []
    # ノードから
    for node in result.nodes:
        name = node.tags.get("name")
        if name:
            stations.append({
                "type": "node",
                "id": node.id,
                "name": name,
                "lat": float(node.lat),
                "lon": float(node.lon)
            })

    # ウェイ（center）から
    for way in result.ways:
        name = way.tags.get("name")
        if name and way.center_lat is not None and way.center_lon is not None:
            stations.append({
                "type": "way",
                "id": way.id,
                "name": name,
                "lat": float(way.center_lat),
                "lon": float(way.center_lon)
            })

    # リレーション（center）から
    for rel in result.relations:
        name = rel.tags.get("name")
        if name and rel.center_lat is not None and rel.center_lon is not None:
            stations.append({
                "type": "relation",
                "id": rel.id,
                "name": name,
                "lat": float(rel.center_lat),
                "lon": float(rel.center_lon)
            })

    # JSON に書き出し
    with open(output_path, "w", encoding="utf-8") as fp:
        json.dump(stations, fp, ensure_ascii=False, indent=2)

    print(f"完了: {len(stations)} 件の駅データを {output_path} に保存しました。")

if __name__ == "__main__":
    fetch_all_stations()

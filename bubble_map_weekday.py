#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import folium
import math
import matplotlib.pyplot as plt
from folium.plugins import HeatMap

# --- 設定項目 -----------------------------------

# 対象の時間帯（ラベル: 時間(0-23)）
time_labels = {
    'morning': 8,
    'noon'   : 12,
    'evening': 18,
}

day = 'weekday'

# 時間帯ごとの人口ファクター（例：実データに合わせて調整）
time_factors = {
    'weekday': {
        8:  0.70,
        12: 0.93,
        18: 0.80,
    },
    'weekend': {
        8:  0.50,
        12: 1.00,
        18: 0.85,
    }
}

# バブル最大半径 (m)
MAX_RADIUS = 300

# --- データ読み込み -----------------------------------

# 町丁ごとの人口＋ジオコーディング済みデータ
df_town = pd.read_csv('miyazaki_city_with_latlon.csv', encoding='utf-8')
# 店舗リスト
df_raw  = pd.read_csv('miyazaki_5pachi_geocode.csv', encoding='shift_jis')
df_store = pd.DataFrame({
    'name':    df_raw['ホール名'],
    'size':    df_raw['P台数'] + df_raw['S台数'],
    'lat':     df_raw['緯度'],
    'lon':     df_raw['経度'],
})

# 総人口（静的）
pop_total = df_town['population'].sum()

# ハフモデルで距離を計算する関数
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# まとめ用データフレーム初期化
summary = pd.DataFrame({ 'name': df_store['name'] })

# --- 各時間帯の処理ループ -----------------------------------
for label, hour in time_labels.items():
    factor = time_factors[day].get(hour, 1.0)
    print(f"Simulating {day} at {hour:02d}:00 (factor={factor})")

    # 動的人口
    pop_dyn = df_town['population'] * factor
    pop_dyn_sum = pop_dyn.sum()

    # Huffモデル→店舗シェア計算
    shares = []
    for _, store in df_store.iterrows():
        # 各町丁との距離
        dists = df_town.apply(
            lambda t: haversine(t['latitude'], t['longitude'], store['lat'], store['lon']) + 1e-6,
            axis=1
        )
        weights = store['size'] / (dists ** 1.5)  # α=1.5 固定 or 任意に変えられます
        # 町丁ごとの選択確率 Pij
        Pij = weights / weights.sum()
        # 店舗シェア = Σ(人口_dyn_i * Pij_i) / Σ(pop_dyn_i)
        share = (pop_dyn * Pij).sum() / pop_dyn_sum
        shares.append(share)

    # ① 個別CSV出力
    out_csv = f'store_shares_{day}_{label}.csv'
    df_out = pd.DataFrame({
        'name': df_store['name'],
        'share': shares
    }).sort_values('share', ascending=False).reset_index(drop=True)
    df_out.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"  -> {out_csv}")

    # ② 個別棒グラフPNG出力
    plt.figure(figsize=(6,4))
    plt.barh(df_out['name'], df_out['share'], color='orange')
    plt.title(f"店舗シェア予測 ({day} {hour:02d}:00)")
    plt.xlabel("予測シェア")
    plt.gca().invert_yaxis()
    png_out = f'store_shares_{day}_{label}.png'
    plt.tight_layout()
    plt.savefig(png_out, dpi=150)
    plt.close()
    print(f"  -> {png_out}")

    # ③ バブルマップHTML出力
    #   バブル半径 = share / max_share * MAX_RADIUS
    max_share = max(shares)
    m = folium.Map(
        location=[df_town['latitude'].mean(), df_town['longitude'].mean()],
        zoom_start=12,
        control_scale=True
    )
    for s, share in zip(df_store.itertuples(), shares):
        r = (share / max_share) * MAX_RADIUS
        folium.Circle(
            location=[s.lat, s.lon],
            radius=r,
            color=None,
            fill=True,
            fill_opacity=0.6,
            popup=f"{s.name}\nshare={share:.3f}"
        ).add_to(m)
    html_out = f'bubble_map_{day}_{label}.html'
    m.save(html_out)
    print(f"  -> {html_out}")

    # ④ まとめ用データに追加
    summary[f'share_{label}'] = shares

# --- まとめCSV & 棒グラフ -----------------------------------
summary_csv = f'store_shares_{day}_summary.csv'
summary.to_csv(summary_csv, index=False, encoding='utf-8')
print(f"Summary CSV -> {summary_csv}")

# 比較用棒グラフ
plt.figure(figsize=(8,6))
for label in time_labels:
    plt.plot(
        summary['name'],
        summary[f'share_{label}'],
        marker='o',
        label=label
    )
plt.xticks(rotation=45, ha='right')
plt.ylabel("予測シェア")
plt.title(f"時間帯別シェア比較 ({day})")
plt.legend()
plt.tight_layout()
cmp_png = f'store_shares_{day}_comparison.png'
plt.savefig(cmp_png, dpi=150)
plt.close()
print(f"Comparison plot -> {cmp_png}")

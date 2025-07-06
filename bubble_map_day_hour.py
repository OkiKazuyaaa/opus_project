# 時間帯・曜日別Huffモデルシミュレーションスクリプト
# 使い方: python time_weekly_simulation.py --day weekday --hour 12

import argparse
import pandas as pd
import numpy as np
import folium
import math
import branca.colormap as cm

# --- 引数定義 ---
parser = argparse.ArgumentParser(description='時間帯・曜日別Huffモデルシミュレーション')
parser.add_argument('--day', choices=['weekday', 'weekend'], default='weekday',
                    help='曜日タイプ (weekday or weekend)')
parser.add_argument('--hour', type=int, choices=range(0,24), default=12,
                    help='時間帯 (0–23)')
args = parser.parse_args()

day_type = args.day
hour = args.hour
print(f"Simulating for {day_type} at {hour}:00")

# --- 時間帯人口比率 (例: 実データに置き換えてください) ---
# 町丁ごとの基準人口に乗ずる比率を時間帯・曜日で指定
time_factors = {
    'weekday': {h: 0.5 + 0.5 * np.sin((h-8)/24 * 2*np.pi) for h in range(24)},
    'weekend': {h: 0.6 + 0.4 * np.cos((h-12)/24 * 2*np.pi) for h in range(24)}
}
# ---------------------------------------------------

# Haversine距離計算
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = map(math.radians, (lat1, lat2))
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- データ読み込み ---
town_csv = 'miyazaki_city_with_latlon.csv'  # 町丁人口・緯度経度
store_csv = 'miyazaki_5pachi_geocode.csv'  # 店舗リスト

df_town = pd.read_csv(town_csv, encoding='utf-8')
s = pd.read_csv(store_csv, encoding='shift_jis')

df_store = pd.DataFrame({
    'name': s['ホール名'],
    'size': s['P台数'] + s['S台数'],
    'lat': s['緯度'],
    'lon': s['経度']
})

# 動的人口列
factor = time_factors[day_type][hour]
print(f"Population factor: {factor:.2f}")
df_town['pop_dynamic'] = df_town['population'] * factor

total_pop = df_town['pop_dynamic'].sum()

# Huffモデル計算
alpha = 1.5  # 距離減衰係数
shares = np.zeros(len(df_store))
for _, town in df_town.iterrows():
    lat_t, lon_t, pop_i = town['latitude'], town['longitude'], town['pop_dynamic']
    if pd.isnull(lat_t) or pd.isnull(lon_t) or pop_i <= 0:
        continue
    d = df_store.apply(lambda r: haversine(lat_t, lon_t, r['lat'], r['lon'])+1e-6, axis=1)
    w = df_store['size'] / (d ** alpha)
    if w.sum() <= 0:
        continue
    p = w / w.sum()
    shares += pop_i * p

df_store['share'] = shares / total_pop

# カラーマップ設定
max_share = df_store['share'].max()
colormap = cm.linear.YlOrRd_09.scale(0, max_share)
colormap.caption = f'Share ({day_type} {hour}:00)'

# マップ中心 (人口重心)
center_lat = (df_town['latitude'] * df_town['pop_dynamic']).sum() / total_pop
center_lon = (df_town['longitude'] * df_town['pop_dynamic']).sum() / total_pop
m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)
m.add_child(colormap)

# バブル描画 (半径固定 200m)
for _, r in df_store.iterrows():
    if pd.isnull(r['lat']) or pd.isnull(r['lon']):
        continue
    color = colormap(r['share'])
    folium.Circle(
        location=[r['lat'], r['lon']],
        radius=200,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=f"{r['name']}\nShare: {r['share']:.2%}"  
    ).add_to(m)

# 保存
env_file = f'bubble_map_{day_type}_{hour}.html'
m.save(env_file)
print(f"Saved map: {env_file}")

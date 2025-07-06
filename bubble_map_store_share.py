# バブルマップで店舗シェア可視化するスクリプト（色付き＆最大半径300m）
import pandas as pd
import numpy as np
import folium
import math
import branca.colormap as cm

# --- 設定 ---
town_csv = 'miyazaki_city_with_latlon.csv'
store_csv = 'miyazaki_5pachi_geocode.csv'
alpha = 1.5  # 距離減衰係数
max_bubble_radius_m = 300  # 最大バブル半径（メートル）
min_bubble_radius_m = 50   # 最小バブル半径（メートル）
# ----------------

# Haversine距離計算関数
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = map(math.radians, (lat1, lat2))
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# データ読み込み
s = pd.read_csv(store_csv, encoding='shift_jis')
t = pd.read_csv(town_csv, encoding='utf-8')

df_store = pd.DataFrame({
    'name': s['ホール名'],
    'size': s['P台数'] + s['S台数'],
    'lat': s['緯度'],
    'lon': s['経度']
})

total_pop = t['population'].sum()
# Huffモデル計算
shares = np.zeros(len(df_store))
for _, town in t.iterrows():
    lat_t, lon_t, pop_i = town['latitude'], town['longitude'], town['population']
    if pd.isnull(lat_t) or pd.isnull(lon_t) or pd.isnull(pop_i):
        continue
    d = df_store.apply(lambda r: haversine(lat_t, lon_t, r['lat'], r['lon'])+1e-6, axis=1)
    w = df_store['size'] / (d ** alpha)
    if w.sum() <= 0:
        continue
    p = w / w.sum()
    shares += pop_i * p

# 市場シェア列
df_store['share'] = shares / total_pop

# カラーマップ設定（0〜最大シェア）
max_share = df_store['share'].max()
colormap = cm.linear.YlOrRd_09.scale(0, max_share)
colormap.caption = '店舗シェア'

# 町丁の人口重心を中心に設定
town_center_lat = (t['latitude']*t['population']).sum()/total_pop
town_center_lon = (t['longitude']*t['population']).sum()/total_pop
m = folium.Map(location=[town_center_lat, town_center_lon], zoom_start=12)
# カラーマップレジェンド追加
m.add_child(colormap)

# バブル描画
for _, r in df_store.iterrows():
    lat, lon, share = r['lat'], r['lon'], r['share']
    if pd.isnull(lat) or pd.isnull(lon):
        continue
    # 半径: share 比率で動的
    radius = max(min((share/max_share)*max_bubble_radius_m, max_bubble_radius_m), min_bubble_radius_m)
    color = colormap(share)
    folium.Circle(
        location=[lat, lon],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=f"{r['name']}\nShare: {share:.2%}"  
    ).add_to(m)

# 保存
m.save('bubble_map_store_share.html')
print('バブルマップを出力しました: bubble_map_store_share.html')

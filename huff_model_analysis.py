# Huffモデルによるシェア予測とヒートマップ作成スクリプト（新店舗CSVをShift-JIS対応で読み込み）
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
import math

# --- ハフモデルのパラメータ ---
alpha = 1.5  # 距離減衰係数
# -----------------------------

# 1. データ読み込み
# 町丁別人口データ（緯度経度付き、UTF-8）
df_town = pd.read_csv('miyazaki_city_with_latlon.csv', encoding='utf-8')
# 新店舗リスト（ジオコード済み CSV、Shift-JIS）
df_raw_store = pd.read_csv('miyazaki_5pachi_geocode.csv', encoding='shift_jis')
# 必要な列を整形：name, size, lat, lon
df_store = pd.DataFrame({
    'name': df_raw_store['ホール名'],
    'size': df_raw_store['P台数'] + df_raw_store['S台数'],
    'lat': df_raw_store['緯度'],
    'lon': df_raw_store['経度']
})

# 2. 距離計算関数（Haversine）
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # 地球半径（km）
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 3. Huff確率の計算
df_town['huff_share'] = np.nan
for idx, town in df_town.iterrows():
    # 緯度経度欠損はスキップ
    if pd.isnull(town['latitude']) or pd.isnull(town['longitude']):
        continue
    # 各店舗までの距離
    dists = df_store.apply(
        lambda s: haversine(town['latitude'], town['longitude'], s['lat'], s['lon']) + 1e-6,
        axis=1
    )
    attractiveness = df_store['size']
    weights = attractiveness / (dists ** alpha)
    P = weights / weights.sum()
    df_town.at[idx, 'huff_share'] = P.max()

# 4. NaN行の除去
df_town = df_town.dropna(subset=['latitude', 'longitude', 'huff_share']).reset_index(drop=True)

# 5. 可視化用Foliumマップ作成
# 中心は人口重心
total_pop = df_town['population'].sum()
centroid_lat = (df_town['latitude'] * df_town['population']).sum() / total_pop
centroid_lon = (df_town['longitude'] * df_town['population']).sum() / total_pop
m = folium.Map(location=[centroid_lat, centroid_lon], zoom_start=12, control_scale=True)

# 6. Huffヒートマップレイヤー
heat_data = df_town[['latitude', 'longitude', 'huff_share']].values.tolist()
HeatMap(
    heat_data,
    name='Huffモデル予測シェア',
    min_opacity=0.4,
    radius=25,
    blur=15,
    max_zoom=12,
    max_val=1.0
).add_to(m)

# 7. 店舗マーカー
marker_cluster = MarkerCluster(name='店舗一覧').add_to(m)
for _, store in df_store.iterrows():
    if pd.isnull(store['lat']) or pd.isnull(store['lon']):
        continue
    folium.Marker(
        location=[store['lat'], store['lon']],
        popup=f"{store['name']} (size={store['size']})",
        icon=folium.Icon(color='blue', icon='home')
    ).add_to(marker_cluster)

# 8. レイヤー切り替えを追加
folium.LayerControl().add_to(m)

# 9. 結果保存
output_file = 'miyazaki_city_huff_analysis_map.html'
m.save(output_file)
print(f"Huffモデル可視化マップを出力しました: {output_file}")

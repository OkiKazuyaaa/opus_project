import pandas as pd
import folium
from folium.plugins import HeatMap
import math

# 感度分析用αリスト
alphas = [1.0, 1.2, 1.5, 1.8, 2.0]

# データ読み込み
df_town  = pd.read_csv('miyazaki_city_with_latlon.csv', encoding='utf-8')
df_raw   = pd.read_csv('miyazaki_5pachi_geocode.csv',   encoding='shift_jis')
df_store = pd.DataFrame({
    'name': df_raw['ホール名'],
    'size': df_raw['P台数'] + df_raw['S台数'],
    'lat':  df_raw['緯度'],
    'lon':  df_raw['経度']
})

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = map(math.radians, (lat1, lat2))
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# マップの中心を人口重心に設定
total_pop  = df_town['population'].sum()
center_lat = (df_town['latitude'] * df_town['population']).sum() / total_pop
center_lon = (df_town['longitude'] * df_town['population']).sum() / total_pop

m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)

# αごとにHeatMapレイヤーを追加
for alpha in alphas:
    col = f'huff_{alpha}'
    # Huffシェア計算
    shares = []
    for _, town in df_town.iterrows():
        lat_t, lon_t = town['latitude'], town['longitude']
        if pd.isnull(lat_t) or pd.isnull(lon_t):
            shares.append(None)
            continue
        dists = df_store.apply(
            lambda s: haversine(lat_t, lon_t, s['lat'], s['lon']) + 1e-6,
            axis=1
        )
        weights = df_store['size'] / (dists ** alpha)
        P = weights / weights.sum()
        shares.append(P.max())
    df_town[col] = shares

    # 有効データのみ抽出
    df_map = df_town.dropna(subset=[col])
    heat_data = df_map[['latitude', 'longitude', col]].values.tolist()

    HeatMap(
        heat_data,
        name=f'α={alpha}',
        radius=20,
        blur=15,
        min_opacity=0.3
    ).add_to(m)

# 店舗一覧レイヤー
stores = folium.FeatureGroup(name='店舗一覧')
for _, r in df_store.iterrows():
    if pd.notnull(r['lat']) and pd.notnull(r['lon']):
        stores.add_child(
            folium.Marker(
                location=[r['lat'], r['lon']],
                popup=f"{r['name']} (size={r['size']})",
                icon=folium.Icon(color='blue', icon='home')
            )
        )
m.add_child(stores)

# レイヤーコントロールを追加
folium.LayerControl(collapsed=False).add_to(m)

# HTML出力
m.save('huff_alpha_layers_map.html')
print("「huff_alpha_layers_map.html」を出力しました。")

import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster

# 1. データ読み込み
# 作業ディレクトリにあるCSVファイルを指定（エンコーディングutf-8）
df = pd.read_csv('miyazaki_city_with_latlon.csv', encoding='utf-8')

# 2. NaNを含む行を除去（緯度経度がないポイントを除く）
df = df.dropna(subset=['latitude', 'longitude']).reset_index(drop=True)

# 3. 人口重心の計算
total_population = df['population'].sum()
centroid_lat = (df['latitude'] * df['population']).sum() / total_population
centroid_lon = (df['longitude'] * df['population']).sum() / total_population

# 4. Foliumマップの作成
m = folium.Map(location=[centroid_lat, centroid_lon], zoom_start=12, control_scale=True)

# 5. ポイントクラスタ（CircleMarker）レイヤー
marker_cluster = MarkerCluster(name='町丁目ポイント').add_to(m)
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=4,
        popup=f"{row['address']} ({row['population']}人)",
        fill=True,
        fill_opacity=0.7
    ).add_to(marker_cluster)

# 6. ヒートマップレイヤー
heat_data = df[['latitude', 'longitude', 'population']].values.tolist()
HeatMap(heat_data, name='人口ヒートマップ', radius=25, blur=15, max_zoom=12).add_to(m)

# 7. 人口重心マーカーを追加
folium.Marker(
    location=[centroid_lat, centroid_lon],
    popup=f"人口重心\nLat: {centroid_lat:.6f}, Lon: {centroid_lon:.6f}",
    icon=folium.Icon(color='red', icon='star')
).add_to(m)

# 8. レイヤーコントロールと保存
folium.LayerControl().add_to(m)
output_file = 'miyazaki_city_analysis_map.html'
m.save(output_file)
print(f"地図ファイル '{output_file}' を生成しました。レイヤー切替可能です。")

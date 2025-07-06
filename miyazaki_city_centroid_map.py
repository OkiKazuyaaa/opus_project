import pandas as pd
import folium

# 1. データ読み込み
# 作業ディレクトリにあるCSVファイルを指定（エンコーディングutf-8）
df = pd.read_csv('miyazaki_city_with_latlon.csv', encoding='utf-8')

# 2. NaNを含む行を除去（緯度経度がないポイントを除く）
df = df.dropna(subset=['latitude', 'longitude']).reset_index(drop=True)

# 3. 人口重心の計算
total_population = df['population'].sum()
centroid_lat = (df['latitude'] * df['population']).sum() / total_population
centroid_lon = (df['longitude'] * df['population']).sum() / total_population

# 4. Foliumによる地図作成
m = folium.Map(location=[centroid_lat, centroid_lon], zoom_start=12)
for _, row in df.iterrows():
    # 有効な緯度経度のみプロット
    lat, lon = row['latitude'], row['longitude']
    m.add_child(
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            popup=f"{row['address']} ({row['population']}人)",
            fill=True,
        )
    )
# 人口重心をマーカーで表示
folium.Marker(
    location=[centroid_lat, centroid_lon],
    popup=f"人口重心\nLat: {centroid_lat:.6f}, Lon: {centroid_lon:.6f}",
    icon=folium.Icon(color='red', icon='star')
).add_to(m)

# 5. HTMLファイルとして保存
output_file = 'miyazaki_city_centroid_map.html'
m.save(output_file)

print(f"地図ファイル '{output_file}' を生成しました。")

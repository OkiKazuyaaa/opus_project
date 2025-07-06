# plot_od_flows_map.py
import pandas as pd
import folium
from folium import CircleMarker, PolyLine

# ——————————————————————
# 設定
# ——————————————————————
INPUT_XLSX   = "huff_step3_all_in_one.xlsx"
SHEET_NAME   = "flows_detail"
OUTPUT_HTML  = "od_flows_map.html"

# 線の太さ・円の大きさスケーリング用パラメータ
LINE_BASE    = 1    # 最小線幅
LINE_MAX_ADD = 4    # 最大線幅増分
CIRC_BASE    = 5    # ホール円の最小半径
CIRC_MAX_ADD = 15   # ホール円の最大半径増分

# ——————————————————————
# 1. データ読み込み
# ——————————————————————
df = pd.read_excel(INPUT_XLSX, sheet_name=SHEET_NAME)

# 必要列チェック
required = [
    "origin_id","origin_lat","origin_lon",
    "store","shop_lat","shop_lon","flow"
]
for c in required:
    if c not in df.columns:
        raise KeyError(f"列 '{c}' が見つかりません")

# ——————————————————————
# 2. 描画用パラメータ計算
# ——————————————————————
# 線の太さに使う最大 flow
max_flow = df["flow"].max()

# ホールごとに総 flow を集計（円の大きさ用）
df_store = (
    df
    .groupby(["store","shop_lat","shop_lon"], as_index=False)["flow"]
    .sum()
)

# 描画中心はホールの平均座標
center_lat = df_store["shop_lat"].mean()
center_lon = df_store["shop_lon"].mean()

# ——————————————————————
# 3. 地図初期化
# ——————————————————————
m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

# ——————————————————————
# 4. OD線を描画
# ——————————————————————
for _, row in df.iterrows():
    lat_o, lon_o = row["origin_lat"], row["origin_lon"]
    lat_s, lon_s = row["shop_lat"], row["shop_lon"]
    f = row["flow"]
    # 座標欠損 or flowゼロはスキップ
    if pd.isna(lat_o) or pd.isna(lat_s) or f <= 0:
        continue
    # 線幅を flow 比でスケーリング
    width = LINE_BASE + (f / max_flow) * LINE_MAX_ADD
    PolyLine(
        locations=[(lat_o, lon_o), (lat_s, lon_s)],
        weight=width,
        color="blue",
        opacity=0.4
    ).add_to(m)

# ——————————————————————
# 5. ホールを赤い円でプロット
# ——————————————————————
for _, row in df_store.iterrows():
    lat, lon, f, name = row["shop_lat"], row["shop_lon"], row["flow"], row["store"]
    # 円半径を flow 比でスケーリング
    radius = CIRC_BASE + (f / max_flow) * CIRC_MAX_ADD
    CircleMarker(
        location=(lat, lon),
        radius=radius,
        color="red",
        fill=True, fill_color="red", fill_opacity=0.7,
        popup=f"{name}\nExpected Visitors: {f:.0f}"
    ).add_to(m)

# ——————————————————————
# 6. 保存
# ——————————————————————
m.save(OUTPUT_HTML)
print(f"ODフロー地図を出力しました → {OUTPUT_HTML}")

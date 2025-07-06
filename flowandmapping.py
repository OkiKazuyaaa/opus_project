# plot_flows_map.py
import pandas as pd
import folium

# ——————————————————————
# 設定
# ——————————————————————
INPUT_XLSX     = "huff_step3_all_in_one.xlsx"
DETAIL_SHEET   = "flows_detail"       # Step3成果シート
OUTPUT_HTML    = "flows_map.html"

# 円マーカーの大きさ調整用パラメータ
ORIGIN_BASE    = 5    # 起点円の最小半径
STORE_BASE     = 5    # ホール円の最小半径
MAX_STORE_RAD  = 20   # ホール円の最大追加半径

# ——————————————————————
# 1. データ読み込み
# ——————————————————————
df = pd.read_excel(INPUT_XLSX, sheet_name=DETAIL_SHEET)

# 必要列チェック
for col in ["origin_id","origin_lat","origin_lon","population",
            "store","shop_lat","shop_lon","flow"]:
    if col not in df.columns:
        raise KeyError(f"'{col}' 列が見つかりません")

# ——————————————————————
# 2. ホールごとに flow を集計
# ——————————————————————
df_store = (
    df
    .groupby(["store","shop_lat","shop_lon"], as_index=False)["flow"]
    .sum()
)

# ——————————————————————
# 3. 地図の初期化 (宮崎県中心にズーム)
# ——————————————————————
# ホールの平均緯度経度を中心に
center_lat = df_store["shop_lat"].mean()
center_lon = df_store["shop_lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

# ——————————————————————
# 4. 起点（地区）を青丸でプロット
# ——————————————————————
# 重複する起点は一度だけ
df_orig = df.drop_duplicates(subset="origin_id")
pop_max = df_orig["population"].max()

for _, row in df_orig.iterrows():
    # 人口比で半径をスケーリング
    rad = ORIGIN_BASE + (row["population"] / pop_max) * ORIGIN_BASE
    folium.CircleMarker(
        location=[row["origin_lat"], row["origin_lon"]],
        radius=rad,
        color="blue",
        fill=True, fill_color="blue", fill_opacity=0.6,
        popup=(
            f"地域ID: {row['origin_id']}<br>"
            f"人口: {int(row['population']):,}"
        )
    ).add_to(m)

# ——————————————————————
# 5. ホールを赤丸でプロット
# ——————————————————————
flow_max = df_store["flow"].max()

for _, row in df_store.iterrows():
    # flow比で半径をスケーリング
    rad = STORE_BASE + (row["flow"] / flow_max) * MAX_STORE_RAD
    folium.CircleMarker(
        location=[row["shop_lat"], row["shop_lon"]],
        radius=rad,
        color="red",
        fill=True, fill_color="red", fill_opacity=0.6,
        popup=(
            f"{row['store']}<br>"
            f"Expected Visitors: {row['flow']:.0f}"
        )
    ).add_to(m)

# ——————————————————————
# 6. ファイル出力
# ——————————————————————
m.save(OUTPUT_HTML)
print(f"地図を出力しました → {OUTPUT_HTML}")

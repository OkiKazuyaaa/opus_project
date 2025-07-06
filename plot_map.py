# plot_map.py

import pandas as pd
import folium

# ────────────────────────────
# 設定
# ────────────────────────────
INPUT_XLSX  = "huff_step3_simple_results.xlsx"  # ご自分のファイル名に合わせてください
OUTPUT_HTML = "map.html"

# Excel 上のカラム名 → スクリプト内で使う名前 のマッピング
COL_MAP = {
    '緯度':               'lat',
    '経度':               'lon',
    'ホール名':           'store',
    'Expected_Visitors': 'flow'
}

# ────────────────────────────
# 1. 最初のシートを読み込む
# ────────────────────────────
xls    = pd.ExcelFile(INPUT_XLSX)
sheet  = xls.sheet_names[0]
print(f"Loading `{INPUT_XLSX}` → sheet `{sheet}`")
df     = pd.read_excel(INPUT_XLSX, sheet_name=sheet)

# ────────────────────────────
# 2. カラム名のリネーム
# ────────────────────────────
df = df.rename(columns=COL_MAP)

# 必須カラムが揃っているかチェック
for c in ('lat', 'lon', 'store', 'flow'):
    if c not in df.columns:
        raise KeyError(f"列 `{c}` が見つかりません。Excel のカラム名を確認してください。")

# 緯度・経度・flow が欠損している行は除外
valid = df.dropna(subset=['lat','lon','flow'])
if valid.empty:
    raise ValueError("有効な緯度・経度・flow データが一件もありません。")

# ────────────────────────────
# 3. マップの中心と最大値を決定
# ────────────────────────────
center     = [ valid['lat'].mean(), valid['lon'].mean() ]
max_flow   = valid['flow'].max()

# ────────────────────────────
# 4. Folium でプロット
# ────────────────────────────
m = folium.Map(location=center, zoom_start=11)# plot_map.py
import pandas as pd
import folium

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
# Huff モデル Step3 一括出力ファイル
INPUT_FILE       = "huff_step3_all_in_one.xlsx"
STORE_SHEET      = "flows_by_store"    # 店舗ごとの期待来店者数シート

# 元ホールデータ（緯度経度入り）
GEO_FILE         = "miyazaki_5pachi_geocode.xlsx"
GEO_SHEET        = "Sheet1"            # 緯度経度を保持するシート名

# 出力 HTML
OUTPUT_MAP       = "map.html"

# プロットに使う列名
STORE_COL        = "store"
LAT_COL          = "緯度"
LON_COL          = "経度"
VALUE_COL        = "expected_visitors"

# ──────────────────────────────────────────────
# 1. データ読み込み・マージ
# ──────────────────────────────────────────────
print("1) データ読み込み…")
df_val = pd.read_excel(INPUT_FILE, sheet_name=STORE_SHEET)
df_geo = pd.read_excel(GEO_FILE, sheet_name=GEO_SHEET)

# 緯度経度列名確認
if STORE_COL not in df_val.columns:
    raise KeyError(f"期待来店者数シートに「{STORE_COL}」列がありません。")
if VALUE_COL not in df_val.columns:
    raise KeyError(f"期待来店者数シートに「{VALUE_COL}」列がありません。")
if 'ホール名' not in df_geo.columns or LAT_COL not in df_geo.columns or LON_COL not in df_geo.columns:
    raise KeyError(f"緯度経度ファイルに必要な列がありません。")

# マージ
df = pd.merge(
    df_val,
    df_geo[['ホール名', LAT_COL, LON_COL]],
    left_on=STORE_COL, right_on='ホール名',
    how='left'
)

# マージ漏れチェック
miss = df[LAT_COL].isna().sum()
if miss:
    print(f"⚠️ {miss} 件の店舗で緯度経度が見つかりませんでした。")

# 有効な行だけ
df = df.dropna(subset=[LAT_COL, LON_COL, VALUE_COL])

# ──────────────────────────────────────────────
# 2. 地図の初期化
# ──────────────────────────────────────────────
# 中心は全店舗の平均緯度経度
center_lat = df[LAT_COL].mean()
center_lon = df[LON_COL].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

# ──────────────────────────────────────────────
# 3. 円マーカー追加
# ──────────────────────────────────────────────
max_val = df[VALUE_COL].max()

for _, row in df.iterrows():
    val = row[VALUE_COL]
    # 半径は 5 ～ 25 の範囲でスケーリング
    radius = 5 + (val / max_val) * 20
    folium.CircleMarker(
        location=(row[LAT_COL], row[LON_COL]),
        radius=radius,
        popup=folium.Popup(
            f"{row[STORE_COL]}<br>"
            f"期待来店者数: {val:.0f}",
            max_width=200
        ),
        color=None,
        fill=True,
        fill_color="crimson",
        fill_opacity=0.6
    ).add_to(m)

# ──────────────────────────────────────────────
# 4. HTML 保存
# ──────────────────────────────────────────────
m.save(OUTPUT_MAP)
print(f"完了！地図を {OUTPUT_MAP} に保存しました。")


for _, row in valid.iterrows():
    # マーカー半径を flow の大小に応じてスケーリング
    radius = (row['flow'] / max_flow) * 20 + 2

    popup_html = (
        f"<b>{row['store']}</b><br>"
        f"期待来店: {row['flow']:.0f}"
    )

    folium.CircleMarker(
        location=[ row['lat'], row['lon'] ],
        radius=radius,
        popup=popup_html,
        fill=True,
        fill_opacity=0.6,
        weight=0
    ).add_to(m)

# ────────────────────────────
# 5. HTML に保存
# ────────────────────────────
m.save(OUTPUT_HTML)
print(f"Map saved to `{OUTPUT_HTML}`")

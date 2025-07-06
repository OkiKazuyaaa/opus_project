import pandas as pd

# ===== ① 売上データの読み込み =====
df_sales = pd.read_csv("all_sales_merged.csv", encoding="utf-8")
df_sales["日付"] = pd.to_datetime(df_sales["日付"], errors="coerce")

# ===== ② 気象データの読み込み =====
df_weather = pd.read_csv("data.csv", encoding="shift_jis", header=2)

# カラム名の整形（必要なものだけ）
df_weather = df_weather.rename(columns={
    "年月日": "日付",
    "平均気温(℃)": "平均気温",
    "最高気温(℃)": "最高気温",
    "最低気温(℃)": "最低気温",
    "日照時間(h)": "日照時間",
    "降水量の合計(mm)": "降水量"  # ← 任意で追加された場合
})
df_weather["日付"] = pd.to_datetime(df_weather["日付"], errors="coerce")

# ===== ③ 売上と天気データのマージ（日付キー） =====
df_merged = pd.merge(df_sales, df_weather, on="日付", how="left")

# ===== ④ 不要な列を削除（任意） =====
drop_cols = [col for col in df_merged.columns if "品質" in col or "Unnamed" in col]
df_merged.drop(columns=drop_cols, inplace=True, errors="ignore")

# ===== ⑤ 結果確認・保存 =====
print(df_merged.head())

# 保存（任意）
df_merged.to_csv("merged_sales_weather.csv", index=False, encoding="utf-8-sig")
print("✅ 売上と気象データの結合が完了しました：merged_sales_weather.csv")

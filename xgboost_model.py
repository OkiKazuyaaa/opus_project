import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# ファイル読み込み
df = pd.read_csv("merged_sales_weather.csv", encoding="utf-8")

# === 前処理 ===

# 台売上合計を数値型に変換（エラーがあればNaNに）
df["台売上合計"] = pd.to_numeric(df["台売上合計"], errors="coerce")

# モデルに不要な列（目的変数と識別子）を除外
drop_cols = ["日付", "曜日_x", "曜日_y"]
df_model = df.drop(columns=drop_cols, errors='ignore')

# 目的変数
target_col = "台売上合計"

# 説明変数のうちobject型（文字列）の列をダミー変数に変換
df_model = pd.get_dummies(df_model)

# 目的変数を再代入
df_model[target_col] = df["台売上合計"]

# 欠損値除去
df_model = df_model.dropna()

# 説明変数と目的変数に分ける
X = df_model.drop(columns=[target_col])
y = df_model[target_col]

# === データ分割 ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# === モデル学習 ===
model = XGBRegressor(random_state=42)
model.fit(X_train, y_train)

# === 予測と評価 ===
y_pred = model.predict(X_test)

# 評価指標
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

# 結果出力
print("【モデル評価】")
print(f"MAE（平均絶対誤差）: {mae:.2f}")
print(f"RMSE（二乗平均平方根誤差）: {rmse:.2f}")
print(f"R²（決定係数）: {r2:.4f}")


# === モデル保存 ===
joblib.dump(model, "model_weather.pkl")
print("✅ モデルを model_weather.pkl として保存しました。")
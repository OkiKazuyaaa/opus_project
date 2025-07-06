import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

# ① データ読み込み
df = pd.read_csv("merged_sales_weather.csv", encoding="utf-8")
df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

# ② カラム名統一（気象項目をわかりやすく）
df = df.rename(columns={
    "日照時間(時間)": "日照時間",
    "平均現地気圧(hPa)": "平均気圧",
    "最大風速(m/s)": "最大風速",
    "最大風速(m/s).2": "最大瞬間風速",
    "平均風速(m/s)": "平均風速"
})

# ③ 数値化と整形
df["出玉率"] = df["出玉率"].astype(str).str.replace('%', '', regex=False).astype(float)
df["客滞率"] = df["客滞率"].astype(str).str.replace('%', '', regex=False).astype(float)
df["曜日_x"] = pd.to_numeric(df["曜日_x"], errors="coerce")
df["最大瞬間風速"] = pd.to_numeric(df["最大瞬間風速"], errors="coerce")

# ④ 使用する特徴量と目的変数
features = [
    "曜日_x", "打込", "出玉率", "客滞率", "台数",
    "平均気温", "最高気温", "最低気温", "日照時間",
    "平均気圧", "最大風速", "最大瞬間風速", "平均風速", "降水量"
]
target = "台売上合計"

# ⑤ 数値変換（全カラム）
for col in features + [target]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ⑥ 欠損値をゼロで補完（fillna）し学習用に分離
df_model = df[features + [target]].fillna(0)
X = df_model[features]
y = df_model[target]

# ⑦ データ分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ⑧ モデル学習
model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
model.fit(X_train, y_train)

# ⑨ 精度評価
y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("✅ モデル評価（天候付き + 欠損補完）")
print(f"RMSE: {rmse:.2f}")
print(f"MAE : {mae:.2f}")
print(f"R²  : {r2:.4f}")

# ⑩ モデル保存
joblib.dump(model, "model_weather.pkl")
print("💾 モデル保存完了: model_weather.pkl")

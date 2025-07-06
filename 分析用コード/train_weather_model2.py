import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_squared_error
import os
import re

# --- 安全なファイル名に変換する関数（Windows対応） ---
def safe_filename(s):
    return re.sub(r'[\\/:*?"<>|()\s.]', '_', s)

# --- ステップ0：パス準備 ---
os.makedirs("./model", exist_ok=True)

# --- ステップ1：データ読み込み ---
print("📥 データ読み込み中...")
df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])

# --- ステップ2：目的変数と特徴量定義 ---
target_col = "台売上合計"
drop_cols = ["日付", target_col]
feature_cols = [col for col in df.columns if col not in drop_cols]

X = df[feature_cols].copy()
y = df[target_col].copy()

# --- ステップ3：カテゴリ変数をエンコードし保存 ---
print("🔁 カテゴリ変数をエンコード中...")
for col in X.select_dtypes(include="object").columns:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    safe_col = safe_filename(col)
    joblib.dump(le, f"./model/encoder_{safe_col}.pkl")
    print(f"✅ encoder_{safe_col}.pkl を保存しました")

# --- ステップ4：データ分割 ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- ステップ5：ハイパーパラメータグリッド定義 ---
param_grid = {
    "n_estimators": [100, 300],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.05, 0.1],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
}

# --- ステップ6：GridSearchCVで最適化 ---
print("🔍 ハイパーパラメータ最適化中（GridSearch）...")
model = XGBRegressor(random_state=42, n_jobs=-1)
grid = GridSearchCV(
    model,
    param_grid,
    cv=3,
    scoring="r2",
    verbose=1
)

grid.fit(X_train, y_train)
best_model = grid.best_estimator_

# --- ステップ7：モデル評価 ---
print("📊 最適モデルの評価中...")
y_pred = best_model.predict(X_test)
r2 = r2_score(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred) ** 0.5

print("📈 評価結果")
print(f"✅ R²: {r2:.4f}")
print(f"✅ RMSE: {rmse:.2f}")
print(f"📌 最適パラメータ: {grid.best_params_}")

# --- ステップ8：モデル保存 ---
output_path = "./model/sales_model_optimized.pkl"
joblib.dump(best_model, output_path)
print(f"✅ モデル保存完了：{output_path}")

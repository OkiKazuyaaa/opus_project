import pandas as pd
import numpy as np
import jpholiday
import joblib
from sklearn.model_selection import train_test_split
from catboost import CatBoostRegressor
from build_features import build_features  # 共通の特徴量構築モジュールを使用

# --- データ読み込み ---
df = pd.read_csv("./merged_sales_weather.csv")
df = df[df["台売上合計"] > 0].copy()
df_feat = build_features(df)

# --- 特徴量とターゲット設定 ---
X = df_feat.drop(columns=["台売上合計", "日付"])
y = df_feat["台売上合計"]

# --- CatBoost用カテゴリ変換（文字列に） ---
cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
for col in cat_cols:
    X[col] = X[col].astype(str)

# --- 学習・保存 ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = CatBoostRegressor(
    iterations=1000,
    learning_rate=0.05,
    depth=6,
    random_seed=42,
    early_stopping_rounds=50,
    verbose=100
)

model.fit(X_train, y_train, eval_set=(X_test, y_test), cat_features=cat_cols, use_best_model=True)

# --- 保存 ---
joblib.dump(model, "model_weather.pkl")
print("✅ モデル保存完了：model_weather.pkl")

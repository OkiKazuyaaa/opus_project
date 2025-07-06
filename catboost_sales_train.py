import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from catboost import CatBoostRegressor
import os

# === CONFIG ===
STORE_CSV_PATH = "./merged_sales_weather.csv"
MODEL_OUTPUT_DIR = "./models"

# --- 入力CSVの読み込み ---
df = pd.read_csv(STORE_CSV_PATH, parse_dates=["日付"])
df = df[df["台売上合計"] > 0].copy()

# === 特徴量構築 ===
def build_features(df):
    df_feat = df.copy()
    df_feat["曜日_x"] = df_feat["日付"].dt.strftime("%A")
    df_feat["祝日フラグ"] = df_feat["祝日名"].notnull().astype(int) if "祝日名" in df_feat else 0
    df_feat["給料日前フラグ"] = df_feat["日付"].dt.day.isin([24, 25, 26]).astype(int)
    df_feat["月末フラグ"] = df_feat["日付"].dt.day >= 28
    df_feat["年金支給日前後フラグ"] = df_feat["日付"].apply(lambda d: int(d.month % 2 == 0 and d.day in [14, 15, 16]))
    return df_feat

df_feat = build_features(df)

# === 使用する特徴量 ===
common_features = [
    "曜日_x", "祝日フラグ", "給料日前フラグ", "月末フラグ", "年金支給日前後フラグ",
    "平均気温", "最高気温", "最低気温", "日照時間(時間)", "平均現地気圧(hPa)", "降水量"
]

# === ターゲット分配 ===
targets = {
    "model_hit": "打込",
    "model_profit": "台粗利",
    "model_sales": "台売上"
}

# === ディレクトリ保存 ===
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

# === モデル初期設定 ===
def train_and_save_model(X, y, cat_cols, model_path):
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        early_stopping_rounds=50,
        random_seed=42,
        verbose=100
    )
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train, eval_set=(X_test, y_test), cat_features=cat_cols, use_best_model=True)
    joblib.dump(model, model_path)
    print(f"✅ Saved: {model_path}")

# === 各モデルを訓練 ===
for model_name, target_col in targets.items():
    df_train = df_feat.dropna(subset=[target_col])
    X = df_train[common_features].copy()
    y = df_train[target_col]

    cat_cols = [col for col in X.select_dtypes(include=["object", "category"]).columns]
    for col in cat_cols:
        X[col] = X[col].astype(str)

    model_path = os.path.join(MODEL_OUTPUT_DIR, f"{model_name}.pkl")
    train_and_save_model(X, y, cat_cols, model_path)

print("\n✅ すべてのモデルの訓練および保存が終了")

import pandas as pd
from catboost import CatBoostRegressor
import joblib

# --- データ読み込み
used_features = [
    "曜日_x", "打込", "総打込", "台粗利","台売上", "台数","客帯率","出玉率",
    "平均気温", "最高気温", "最低気温", "日照時間(時間)",
    "平均気圧(hPa)", "最大風速(m/s)", "最大瞬間風速(m/s)", "平均風速(m/s)", "降水量"
]

try:
    df = pd.read_csv("merged_sales_weather.csv", encoding="shift_jis", parse_dates=["日付"])
except UnicodeDecodeError:
    df = pd.read_csv("merged_sales_weather.csv", encoding="cp932", parse_dates=["日付"])

# --- 必要な列だけ抽出
required_columns = used_features + ["台売上合計"]
df = df[[col for col in required_columns if col in df.columns]]

# --- % を除去して float に変換（可能なものだけ）
for col in df.columns:
    try:
        df[col] = df[col].astype(str).str.replace('%', '', regex=True).astype(float)
    except ValueError:
        pass  # 変換できない列（文字列）は無視

# --- NaN除去：目的変数yが欠損していたら削除
df = df.dropna(subset=["台売上合計"])

# --- 説明変数と目的変数の分離
X = df.drop(columns=["台売上合計"])
y = df["台売上合計"]

# --- カテゴリ型列（object）に "missing" を補完
cat_features = X.select_dtypes(include=["object"]).columns.tolist()
for col in cat_features:
    X[col] = X[col].fillna("missing")

# --- モデル構築と学習
model = CatBoostRegressor(
    iterations=2000,
    learning_rate=0.3,
    depth=7,
    cat_features=cat_features,
    loss_function='RMSE',
    verbose=100
)
model.fit(X, y)

# --- モデル保存
joblib.dump(model, "model_weather.pkl")

print("✅ モデル再学習・保存完了（共通特徴量に対応済み）")

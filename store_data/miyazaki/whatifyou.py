import pandas as pd
from catboost import CatBoostRegressor
import joblib

# --- データ読み込み
df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])

# --- % を除去して float に変換（可能なものだけ）
for col in df.columns:
    try:
        df[col] = df[col].astype(str).str.replace('%', '', regex=True).astype(float)
    except ValueError:
        pass  # 変換できない列（文字列）は無視

# --- 目的変数と説明変数の分離
y = df["台売上合計"]
X = df.drop(columns=["日付", "台売上合計"])

# --- ✅ object型（文字列）の列をすべてカテゴリ変数として登録
cat_features = X.select_dtypes(include=["object"]).columns.tolist()

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

# --- 保存
joblib.dump(model, "model_weather.pkl")

print("✅ モデル再学習・保存完了（文字列列も含めて学習）")

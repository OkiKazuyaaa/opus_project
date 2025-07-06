import pandas as pd
import joblib
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from build_features import build_features

# モデル読み込み
model_hit = joblib.load("model_hit.pkl")
model_base = joblib.load("model_sales.pkl")

# データ読み込み
df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])
df.columns = df.columns.str.strip()

# 特徴量生成
df_feat = build_features(df, model_hit=model_hit, model_base=model_base)

# 特徴量列の指定
feature_cols = [
    "曜日_x", "祝日フラグ", "給料日前フラグ", "月末フラグ", "年金支給日前後フラグ",
    "台数", "出玉率", "客滞率", "打込",
    "平均気温", "最高気温", "最低気温", "日照時間(時間)",
    "平均現地気圧(hPa)", "降水量", "最大風速(m/s)", "平均風速(m/s)"
]

X = df_feat[feature_cols]
y = df["台売上合計"]

# カテゴリ変数をダミー変換（XGBoostは数値しか受け取らない）
X_encoded = pd.get_dummies(X, columns=["曜日_x"])

# 学習・テスト分割
X_train, X_test, y_train, y_test = train_test_split(
    X_encoded, y, test_size=0.2, random_state=42
)

# モデル構築（XGBoost）
model_weather = XGBRegressor(
    n_estimators=1000,
    learning_rate=0.03,
    max_depth=6,
    objective="reg:squarederror",  # 安定性のため
    verbosity=1,
    random_state=42
)

# 学習（バージョン互換のため、early_stopping_roundsは省く）
model_weather.fit(X_train, y_train)

# 予測・評価
y_pred = model_weather.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
mape = mean_absolute_percentage_error(y_test, y_pred)

# 結果表示
print("\n--- モデル評価 ---")
print(f"MAE（平均絶対誤差）: {mae:,.0f} 円")
print(f"MAPE（誤差率）: {mape*100:.2f}%")

# モデル保存
joblib.dump(model_weather, "model_weather.pkl")
print("✅ モデル保存完了：model_weather.pkl")

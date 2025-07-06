import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor
from sklearn.metrics import r2_score

# データ読み込み
df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])

# 特徴量と目的変数
target_col = "売上"
drop_cols = ["日付", target_col]
feature_cols = [col for col in df.columns if col not in drop_cols]

X = df[feature_cols]
y = df[target_col]

# カテゴリ変数のエンコード（必要なら）
for col in X.select_dtypes(include="object").columns:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    joblib.dump(le, f"./model/encoder_{col}.pkl")  # エンコーダも保存

# 学習データ分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# XGBoostモデル学習
model = XGBRegressor(n_estimators=100, max_depth=4, random_state=42)
model.fit(X_train, y_train)

# 評価
y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
print(f"R^2スコア: {r2:.4f}")

# モデル保存
joblib.dump(model, "./model/sales_model.pkl")
print("✅ モデル保存完了：./model/sales_model.pkl")

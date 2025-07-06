import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import numpy as np
import joblib

df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])

target_col = "台売上"
drop_cols = ["日付", "売上", "打込合計", "台粗利", "打込"]
feature_cols = [col for col in df.columns if col not in drop_cols + [target_col]]

for col in df[feature_cols].select_dtypes(include='object').columns:
    df[col] = pd.factorize(df[col])[0]

X = df[feature_cols]
y = df[target_col]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = xgb.XGBRegressor(n_estimators=100, max_depth=4, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print(f"✅ 台売上モデル R²: {r2:.3f} / RMSE: {rmse:.2f}")

joblib.dump(model, "model_sales.pkl")
print("✅ model_sales.pkl を保存しました")

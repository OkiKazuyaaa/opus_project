import streamlit as st
import pandas as pd
import joblib
from datetime import timedelta

st.set_page_config(page_title="売上予測シミュレーター", layout="centered")
st.title("🎯 売上予測シミュレーター（XGBoostモデル）")

# モデルとエンコーダーの読み込み
model = joblib.load("./model/sales_model.pkl")
le_weather = joblib.load("./model/weather_encoder.pkl")

# 入力欄
start_date = st.date_input("開始日")
forecast_type = st.radio("予測期間", ["1日", "1週間"], horizontal=True)
hour = st.selectbox("時間帯", [8, 12, 18], index=1)
weather_label = st.selectbox("天気", ["晴れ", "曇り", "雨"])
weather = le_weather.transform([weather_label])[0]
store = st.selectbox("店舗", ["A店", "B店", "C店"])
p_table = {"A店": 400, "B店": 300, "C店": 350}
s_table = {"A店": 200, "B店": 150, "C店": 180}
P = p_table[store]
S = s_table[store]

# 予測実行
if st.button("売上を予測する"):
    if forecast_type == "1日":
        weekday = start_date.weekday()
        X_input = pd.DataFrame([[weekday, hour, weather, P, S]],
            columns=["weekday", "hour", "weather_enc", "P台数", "S台数"])
        y_pred = model.predict(X_input)[0]
        st.success(f"📅 {start_date} の予測売上：¥{int(y_pred):,} 円")

    elif forecast_type == "1週間":
        dates = [start_date + timedelta(days=i) for i in range(7)]
        result = []
        for d in dates:
            weekday = d.weekday()
            X_input = pd.DataFrame([[weekday, hour, weather, P, S]],
                columns=["weekday", "hour", "weather_enc", "P台数", "S台数"])
            y_pred = model.predict(X_input)[0]
            result.append({"日付": d, "予測売上": int(y_pred)})

        df_result = pd.DataFrame(result)
        st.dataframe(df_result)
        st.line_chart(df_result.set_index("日付"))
        total = df_result["予測売上"].sum()
        st.success(f"📊 1週間の予測売上合計：¥{int(total):,} 円")

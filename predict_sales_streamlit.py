import streamlit as st
import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Meiryo'  # or 'Yu Gothic', 'IPAexGothic'
from datetime import timedelta

def run_sales_forecast_app():
    st.subheader("売上予測シミュレーター（XGBoostモデル）")

    # モデルとエンコーダーの読み込み
    model = joblib.load("./model/sales_model.pkl")
    le_weather = joblib.load("./model/weather_encoder.pkl")

    # SHAP explainer の初期化
    explainer = shap.Explainer(model)

    # 入力欄
    start_date = st.date_input("開始日")
    forecast_type = st.radio("予測期間", ["1日", "1週間", "1か月", "全店舗（1日）"], horizontal=True)
    hour = st.selectbox("時間帯", [8, 12, 18], index=1)
    weather_label = st.selectbox("天気", ["晴れ", "曇り", "雨"])
    weather = le_weather.transform([weather_label])[0]
    store = st.selectbox("店舗", ["A店", "B店", "C店"])
    p_table = {"A店": 400, "B店": 300, "C店": 350}
    s_table = {"A店": 200, "B店": 150, "C店": 180}
    P = p_table[store]
    S = s_table[store]

    if st.button("売上を予測する"):
        result = []

        if forecast_type == "1日":
            weekday = start_date.weekday()
            X_input = pd.DataFrame([[weekday, hour, weather, P, S]],
                columns=["weekday", "hour", "weather_enc", "P台数", "S台数"])
            y_pred = model.predict(X_input)[0]
            st.success(f"📅 {start_date} の予測売上：¥{int(y_pred):,} 円")
                # SHAPの解釈ステップ
            explainer = shap.Explainer(model)
            shap_values = explainer(X_input)

            # グラフ描画（安全版）
            fig = plt.figure()
            shap.plots.waterfall(shap_values[0], show=False)
            st.pyplot(fig)
            plt.clf()

            # SHAP Waterfall 表示
            st.markdown("#### 🔍 この予測の要因分析 (SHAP)")
            shap_values = explainer(X_input)
            fig = shap.plots.waterfall(shap_values[0], show=False)
            st.pyplot(plt.gcf())
            plt.clf()

        elif forecast_type == "1週間":
            dates = [start_date + timedelta(days=i) for i in range(7)]
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

        elif forecast_type == "1か月":
            dates = [start_date + timedelta(days=i) for i in range(30)]
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
            st.success(f"📅 1か月の予測売上合計：¥{int(total):,} 円")

        elif forecast_type == "全店舗（1日）":
            for store in ["A店", "B店", "C店"]:
                P = p_table[store]
                S = s_table[store]
                weekday = start_date.weekday()
                X_input = pd.DataFrame([[weekday, hour, weather, P, S]],
                    columns=["weekday", "hour", "weather_enc", "P台数", "S台数"])
                y_pred = model.predict(X_input)[0]
                result.append({"店舗": store, "予測売上": int(y_pred)})

            df_result = pd.DataFrame(result)
            st.dataframe(df_result)
            st.bar_chart(df_result.set_index("店舗"))
            total = df_result["予測売上"].sum()
            st.success(f"🏬 全店舗合計（{start_date}）：¥{int(total):,} 円")

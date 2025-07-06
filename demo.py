import streamlit as st
import pandas as pd
import numpy as np
import datetime
import altair as alt

# -------------------------
# ダミーデータの生成
# -------------------------
today = datetime.date.today()
dates = pd.date_range(today - pd.Timedelta(days=2), periods=4)
sales = [1.8, 1.5, 2.3, np.nan]  # 最終日は予測のみ

sales_df = pd.DataFrame({
    "日付": dates,
    "売上": sales
})

factors_df = pd.DataFrame({
    "要因": ["天候", "曜日", "競合施策"],
    "影響度": [0.12, -0.08, -0.05]
})

stores_df = pd.DataFrame({
    "拠点": ["A店", "B店", "C店"],
    "売上予測": [2500000, 1950000, 1800000],
    "差分": ["+4%", "-8%", "+6%"],
    "要因": ["", "雨×競合重複", ""]
})

# -------------------------
# UI 構成
# -------------------------
st.set_page_config(page_title="売上予測 AI ダッシュボード", layout="wide")

st.title("売上予測 AI ダッシュボード")
st.caption("今日・明日・明後日の売上をAIで予測し、要因を分解して表示します")

# 左上：売上予測チャート
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("売上予測")
    line_chart = alt.Chart(sales_df).mark_line(point=True).encode(
        x="日付:T",
        y=alt.Y("売上:Q", scale=alt.Scale(domain=[0, 3]))
    ).properties(height=250)
    st.altair_chart(line_chart, use_container_width=True)

    st.selectbox("店舗", options=["A店", "B店", "C店"])
    st.date_input("日付", value=today)
    st.selectbox("天候", options=["晴れ", "曇り", "雨"])

with col2:
    st.metric(label="明日の推奨アクション", value="+18%", delta="LINE配信を提案")

# 下段：売上要因の分解 + 拠点比較
col3, col4 = st.columns(2)
with col3:
    st.subheader("売上要因の分解")
    bar_chart = alt.Chart(factors_df).mark_bar().encode(
        x="影響度:Q",
        y=alt.Y("要因:N", sort="-x"),
        color=alt.Color("要因:N")
    )
    st.altair_chart(bar_chart, use_container_width=True)

with col4:
    st.subheader("拠点比較・ランキング")
    st.dataframe(stores_df, use_container_width=True)
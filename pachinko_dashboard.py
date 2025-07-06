import streamlit as st
st.set_page_config(page_title="売上AI分析ダッシュボード", layout="wide")
import pandas as pd
import altair as alt
import math
import folium
import shap
import os
import json
import joblib
import numpy as np
import tempfile
import random
from scipy.stats import linregress
from io import StringIO
from folium.plugins import HeatMap
from streamlit_folium import folium_static
from datetime import date, timedelta
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from fpdf import FPDF
import matplotlib.font_manager as fm
import streamlit.components.v1 as components
import base64
import time
from datetime import datetime
import csv
from datetime import datetime, timedelta
import bcrypt
from catboost import CatBoostRegressor
import jpholiday
import pandas as pd
import seaborn as sns



# def build_features(df):
#     import numpy as np
#     import jpholiday
#     df_feat = df.copy()
#     df_feat["日付"] = pd.to_datetime(df_feat["日付"])
#     df_feat["曜日_x"] = df_feat["日付"].dt.strftime("%A")
#     df_feat["祝日名"] = df_feat["日付"].apply(lambda x: jpholiday.is_holiday_name(x) if jpholiday.is_holiday(x) else "平日")
#     df_feat["祝日フラグ"] = df_feat["祝日名"].apply(lambda x: int(x != "平日"))
#     df_feat["給料日前フラグ"] = df_feat["日付"].dt.day.isin([24, 25, 26]).astype(int)

#     #df_feat["週番号"] = df_feat["日付"].dt.isocalendar().week.astype(int)

#     # 天気カラム補完（予測時は欠損になる可能性あり）
#     weather_cols = ["平均気温", "最高気温", "最低気温", "日照時間(時間)", "平均現地気圧(hPa)", "降水量"]
#     for col in weather_cols:
#         if col not in df_feat.columns:
#             df_feat[col] = np.nan

#     return df_feat



# --- ユーザーデータを読み込む ---
with open("users.json", "r", encoding="utf-8") as f:
    USER_DB = json.load(f)

#ログイン記録
if "login_failures" not in st.session_state:
    st.session_state.login_failures = 0

if "login_locked_until" not in st.session_state:
    st.session_state.login_locked_until = None

# --- 店舗名の取得とマッピング ---
store_name = st.session_state.get("store_name", "店舗名未設定")

# --- 日本語表示名（st.session_stateにある）→ マッピング名（ファイルパス用）に変換
store_name_map = {
    "宮崎本店": "オーパス宮崎本店",
    "小松台店": "オーパス小松",
    "都城店": "オーパス都城",
    "高鍋店": "オーパス高鍋",
    "日南店": "オーパス日南",
    "延岡店": "オーパス延岡",
    "三股店": "オーパス三股",
    "鹿屋店": "オーパス鹿屋",
}

mapped_store = store_name_map.get(store_name, store_name)


#操作履歴
def log_page_visit(page_name):
    file_path = "page_access_log.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["日時", "ユーザー", "店舗名", "ページ名"])
        writer.writerow([
            datetime.now().isoformat(),
            st.session_state.get("username", "未ログイン"),
            st.session_state.get("store_name", "不明店舗"),
            page_name
        ])



# --- IPアドレス取得 ---
import requests

def get_client_ip():
    try:
        res = requests.get("https://api.ipify.org?format=json", timeout=3)
        return res.json().get("ip", "不明")
    except:
        return "取得失敗"



# フォントパスを絶対パスで指定
font_path = os.path.abspath("fonts/NotoSansJP-Regular.otf")

if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.sans-serif'] = ['Noto Sans JP']
    plt.rcParams['axes.unicode_minus'] = False
else:
    st.warning(f"フォントが見つかりません: {font_path}")

# ログイン履歴
def append_login_history(email, result, store_name="", ip_address="不明"):
    file_path = "login_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["日時", "メールアドレス", "店舗名", "結果", "IPアドレス"])
        writer.writerow([
            datetime.now().isoformat(),
            email,
            store_name,
            result,
            ip_address
        ])





# --- PoC用 簡易ログイン（test@example.com のみ許可） ---
import streamlit as st

# ログイン成功時（認証成功時）
def is_admin():
    return st.session_state.get("username") == "kokoronohitomi2003@keio.jp"







# --- セッション認証管理 ---
if "login_failures" not in st.session_state:
    st.session_state.login_failures = 0

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- ログインロック中かどうか判定 ---
if not st.session_state.authenticated:
    locked_until = st.session_state.get("login_locked_until")
    now = datetime.now()

    if locked_until and now < locked_until:
        remaining = int((locked_until - now).total_seconds())

        st.warning(f"ログイン失敗が続いています。あと {remaining} 秒後に再入力できます。")

        # カウントダウン表示（省略可：上記で済む場合）
        import streamlit.components.v1 as components
        html_code = f"""
        <div style="text-align:center; font-size:24px; color:#cc8800;">
          <p id="cd_msg">あと {remaining} 秒で再入力できます</p>
        </div>
        <script>
          let sec = {remaining};
          const msg = document.getElementById("cd_msg");
          const interval = setInterval(() => {{
            sec--;
            if (sec <= 0) {{
              location.reload();  // 自動リロードでフォーム復活
              clearInterval(interval);
            }} else {{
              msg.textContent = `あと ${{
                sec
              }} 秒で再入力できます`;
            }}
          }}, 1000);
        </script>
        """
        components.html(html_code, height=100)
        st.stop() 



    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("miral.png", width=240)
    st.title("MIRALログインへようこそ")
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user = USER_DB.get(email)
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            st.session_state.authenticated = True
            ip_address = get_client_ip()
            append_login_history(email, "成功", user["store_name"], ip_address)
            st.session_state.store_name = user["store_name"]
            st.session_state.username = email  
            st.session_state.just_logged_in = True
            st.session_state.login_failures = 0
            st.success("ログイン成功")
            st.rerun()
        else:
            st.session_state.login_failures += 1
            append_login_history(email, "失敗", ip_address=ip_address)

            if st.session_state.login_failures >= 3:
                st.session_state.login_locked_until = datetime.now() + timedelta(seconds=10)  

                wait_sec = 10 * (st.session_state.login_failures - 2)
                st.warning(f"ログイン試行が複数回失敗しています。{wait_sec}秒待機中...")

                import streamlit.components.v1 as components
                html_code = f"""
                <div style="text-align:center; font-size:24px; color:#ffcc00; margin-top:20px;">
                <p id="cd_msg">あと {wait_sec} 秒で再入力可能です</p>
                </div>
                <script>
                let sec = {wait_sec};
                const msg = document.getElementById("cd_msg");
                const interval = setInterval(() => {{
                    sec--;
                    if (sec <= 0) {{
                    msg.textContent = "再入力できます";
                    clearInterval(interval);
                    }} else {{
                    msg.textContent = `あと ${{
                        sec
                    }} 秒で再入力可能です`;
                    }}
                }}, 1000);
                </script>
                """
                components.html(html_code, height=100)
                import time
                time.sleep(wait_sec)


        st.error("ログイン失敗：メールアドレスまたはパスワードが正しくありません")

    st.markdown("""
    <div style='margin-top: 40px; padding: 16px; background-color: #f9f9f9; border-radius: 8px;'>
        <p style='font-size: 14px; color: #333;'>
            このシステムは MIRAL が開発した業務支援ダッシュボードです。<br>
            セキュリティ保護された環境で運用されており、登録されたユーザーのみがアクセス可能です。
        </p>
        <p style='font-size: 12px; color: #888;'>
            ログイン情報をお持ちでない方は、担当者までご連絡ください。
        </p>
        <p style='font-size: 12px; color: #666; margin-top: 12px;'>
            このサイトはSSL/TLSにより暗号化され、安全に通信されています。
        </p>
        <p style='font-size: 13px; margin-top: 20px;'>
            ログインに関するお問い合わせは <a href="mailto:aspira.information@gmail.com">aspira.information@gmail.com</a> までご連絡ください。
        </p>
        <p style='font-size: 12px; color: #888;'>
            スマートフォンでのご利用は横向き表示を推奨しています。
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <p style='text-align:center; font-size:12px;'>
<a href='https://okikazuyaaa.github.io/miral-policy/privacy.html' target='_blank'>プライバシーポリシー</a> ・
<a href='https://okikazuyaaa.github.io/miral-policy/terms.html' target='_blank'>利用規約</a>
</p>
    """, unsafe_allow_html=True)

    st.stop()


# --- ログイン後の処理 ---管理者確認用-------
if (
    "authenticated" in st.session_state
    and st.session_state.authenticated
    and st.session_state.username == "kokoronohitomi2003@keio.jp"  # 管理者のメールアドレス
):
    if st.button("ログイン履歴を見る（管理者のみ）"):
        try:
            with open("login_history.csv", "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 列数確認して補正
            data = []
            for line in lines:
                parts = line.strip().split(",")
                if len(parts) == 4:
                    parts.append("未記録")  # IPアドレス列を補完
                data.append(parts)

            import pandas as pd
            df = pd.DataFrame(data[1:], columns=["日時", "メールアドレス", "店舗名", "結果", "IPアドレス"])

            st.dataframe(df.sort_values("日時", ascending=False))

        except Exception as e:
            st.error(f"ログ読み込みに失敗しました: {e}")







# ようこそ演出（ログイン直後1回だけ）
if st.session_state.get("just_logged_in", False):
    with open("haikei.jpeg", "rb") as f:
        bg_data = base64.b64encode(f.read()).decode()

    html_code = f"""
    <html>
    <head>
      <style>
        body {{
          margin: 0;
          padding: 0;
          font-family: 'Segoe UI', sans-serif;
          background: url("data:image/jpeg;base64,{bg_data}") no-repeat center center fixed;
          background-size: cover;
          height: 100vh;
          display: flex;
          justify-content: center;
          align-items: center;
          color: white;
        }}
        .overlay {{
          background: rgba(0, 0, 0, 0.5);
          padding: 60px 40px;
          border-radius: 20px;
          box-shadow: 0 8px 20px rgba(0,0,0,0.3);
          text-align: center;
        }}
        h1 {{
          font-size: 40px;
          margin: 0;
        }}
        p {{
          font-size: 20px;
          margin-top: 10px;
        }}
      </style>
    </head>
    <body>
      <div class="overlay">
        <h1>ようこそ、{st.session_state.get('store_name', 'MIRAL')}様</h1>
        <p>ログインありがとうございます</p>
      </div>
    </body>
    </html>
    """

    components.html(html_code, height=600)
    time.sleep(3.5)
    st.session_state.just_logged_in = False
    st.rerun()


# モデルの読み込み（すでにトレーニング済の .cbm）
#model = CatBoostRegressor()
#model.load_model("model_catboost.cbm")

# pkl形式で保存
#joblib.dump(model, "model_weather.pkl")  # ← 元のXGBoost置き換え用

# --- 店舗名の取得 ---
selected_store = st.session_state.get("store_name")

# --- Excelモデルファイル辞書 ---
file_map_excel = {
    "オーパス宮崎本店": "data/2025_miyazaki.xlsx",
    "オーパス小松": "data/2025_komatsu.xlsx",
    "オーパス高鍋": "data/2025_takanabe.xlsx",
    "オーパス日南": "data/2025_nichinan.xlsx",
    "オーパス延岡": "data/2025_nobeoka.xlsx",
    "オーパス三股": "data/2025_mimata.xlsx",
    "オーパス都城": "data/2025_miyakonojo.xlsx",
    "オーパス鹿屋": "data/2025_kanoya.xlsx",
}

file_map_models = {
    "オーパス宮崎本店": {
        "weather": "models/miyazaki/model_weather.pkl",
        "sales": "models/miyazaki/model_sales.pkl",
        "profit": "models/miyazaki/model_profit.pkl",
        "hit": "models/miyazaki/model_hit.pkl",
        "base": "models/miyazaki/model.pkl"
    },
    "オーパス小松": {
        "weather": "models/komatsu/model_weather.pkl",
        "sales": "models/komatsu/model_sales.pkl",
        "profit": "models/komatsu/model_profit.pkl",
        "hit": "models/komatsu/model_hit.pkl",
        "base": "models/komatsu/model.pkl"
    },
    "オーパス高鍋": {
        "weather": "models/takanabe/model_weather.pkl",
        "sales": "models/takanabe/model_sales.pkl",
        "profit": "models/takanabe/model_profit.pkl",
        "hit": "models/takanabe/model_hit.pkl",
        "base": "models/takanabe/model.pkl"
    },
    "オーパス日南": {
        "weather": "models/nichinan/model_weather.pkl",
        "sales": "models/nichinan/model_sales.pkl",
        "profit": "models/nichinan/model_profit.pkl",
        "hit": "models/nichinan/model_hit.pkl",
        "base": "models/nichinan/model.pkl"
    },
    "オーパス延岡": {
        "weather": "models/nobeoka/model_weather.pkl",
        "sales": "models/nobeoka/model_sales.pkl",
        "profit": "models/nobeoka/model_profit.pkl",
        "hit": "models/nobeoka/model_hit.pkl",
        "base": "models/nobeoka/model.pkl"
    },
    "オーパス三股": {
        "weather": "models/mimata/model_weather.pkl",
        "sales": "models/mimata/model_sales.pkl",
        "profit": "models/mimata/model_profit.pkl",
        "hit": "models/mimata/model_hit.pkl",
        "base": "models/mimata/model.pkl"
    },
    "オーパス都城": {
        "weather": "models/miyakonojo/model_weather.pkl",
        "sales": "models/miyakonojo/model_sales.pkl",
        "profit": "models/miyakonojo/model_profit.pkl",
        "hit": "models/miyakonojo/model_hit.pkl",
        "base": "models/miyakonojo/model.pkl"
    },
    "オーパス鹿屋": {
        "weather": "models/kanoya/model_weather.pkl",
        "sales": "models/kanoya/model_sales.pkl",
        "profit": "models/kanoya/model_profit.pkl",
        "hit": "models/kanoya/model_hit.pkl",
        "base": "models/kanoya/model.pkl"
    },
}
# # --- ファイル読み込み関数 _
def load_csv(path, **kwargs):
    if not os.path.exists(path):
        st.error(f"CSVファイルが見つかりません: {path}")
        st.stop()
    return pd.read_csv(path, **kwargs)

def load_excel_store_filtered(path, **kwargs):
    if not os.path.exists(path):
        st.error("該当する店舗の分析ファイルが存在しません。管理者にご連絡ください。")
        st.stop()
    xls = pd.ExcelFile(path)
    df = pd.concat([xls.parse(sheet).assign(対象シート=sheet) for sheet in xls.sheet_names], ignore_index=True)
    df.columns = df.columns.astype(str).str.strip()
    return df

def load_pkl(path):
    if not os.path.exists(path):
        st.error(f"モデルファイルが見つかりません: {path}")
        st.stop()
    return joblib.load(path)

# --- 共通ファイル読み込み（ページ上で使用） ---
mapped_store = store_name_map.get(store_name, store_name)
selected_excel = file_map_excel.get(mapped_store)

if not selected_excel or not os.path.exists(selected_excel):
    st.warning("この店舗には分析ファイルが存在しません。一部のページでは内容が表示されません。")
    df_merged = pd.DataFrame()  # 空のDataFrameを代わりに入れる
else:
    df_merged = load_excel_store_filtered(selected_excel)


# ------------------------------
# ✅ 4. 対応モデルファイルの読み込みに使用
# ------------------------------
model_paths = file_map_models[mapped_store]


model_paths = file_map_models[selected_store]
model = load_pkl(model_paths["weather"])
model_sales = load_pkl(model_paths["sales"])
model_profit = load_pkl(model_paths["profit"])
model_hit = load_pkl(model_paths["hit"])
model_base = load_pkl(model_paths["base"])






if selected_store != "管理者":
    try:
        selected_excel = file_map_excel[selected_store]
    except KeyError:
        st.warning(f"店舗「{selected_store}」に対応するファイルが存在しません。")
else:
    st.info("管理者アカウントでは分析ファイルの選択はスキップされます。")



# --- パス動的生成関数 ---
def get_store_file(filename_template):
    fallback_path = f"data/{filename_template}"  # 共通ファイル
    store_path = f"data/{selected_store}_{filename_template}"  # 店舗ファイル
    return store_path if os.path.exists(store_path) else fallback_path





# タイトルとメニュー

st.title("売上AI分析ダッシュボード")
#store_name = st.session_state.get("store_name", "店舗名未設定")
# --- マッピングされた英語名の取得 ---
mapped_store = store_name_map.get(store_name)
#st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")



# --- ページ一覧と初期選択 ---
pages = {
    "自社ホールの分析": "自社ホールの分析",
    # "月別売上目標ダッシュボード": "月別売上目標ダッシュボード",
    # "売上予測シミュレーター": "売上予測シミュレーター",
    # "売上予測シミュレーター（最適化）": "売上予測シミュレーター（最適化）",
    "売上予測シミュレーターvol.2": "売上予測シミュレーターvol.2",
    "天候付き売上予測シミュレーター": "天候付き売上予測",
    "What-ifシナリオシミュレーター": "What-if分析",
    "時間帯別客数ヒートマップ": "時間帯別客数ヒートマップ",
    "時間帯別売上効率分析": "売上効率ヒートマップ",
    "機種別償却効率分析": "機種別分析",
    "地理マップ分析": "地理マップ",
    "ホール内ランキング": "ホール内ランキング",
    "イベント影響分析": "イベント影響分析",
    "AIコンサルアドバイス": "AIコンサル"
}

if "selected_page" not in st.session_state:
    st.session_state.selected_page = list(pages.keys())[0]

# --- メニュー表示（サイドバー） ---
st.sidebar.markdown("### メニュー")
for page_name, label in pages.items():
    selected = st.session_state.selected_page == page_name
    if selected:
        st.sidebar.markdown(f"""
        <div style="
            display: block;
            width: 100%;
            text-align: left;
            background-color: rgba(255,255,255,0.35);
            border: 1px solid rgba(255,255,255,0.25);
            border-left: 6px solid #a88838;
            border-radius: 14px;
            padding: 16px 24px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            font-weight: bold;
            font-size: 16px;
            color: #2f2f2f;
        ">{label}</div>""", unsafe_allow_html=True)
    else:
        if st.sidebar.button(label, key=f"menu_{page_name}"):
            st.session_state.selected_page = page_name
            st.rerun()


#ログアウト処理
with st.sidebar:
    st.markdown("---")
    if st.button("ログアウト"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()



# ページ全体スタイル：背景色＋フォント＋基本の見た目を整える
page_style = """
<style>
/* 全体背景 */
body, .stApp {
    background-color: #f7f5f0 !important;
    color: #2f2f2f;
    font-family: 'Yu Mincho', serif;
}


/* 見出し装飾 */
h1, h2, h3, h4 {
    font-family: 'Yu Mincho', serif;
    color: #1e1e1e;
}


/* カードっぽい要素 */
div[data-testid="stMetric"] {
    background-color: #ffffffdd;
    padding: 10px;
    border-radius: 12px;
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
    margin-bottom: 8px;
}
</style>
"""
st.markdown(page_style, unsafe_allow_html=True)

# 🔽 ここに追加
def generate_advice(機種名, 償却効率, 粗利, 償却額):
    import random
    if 償却効率 > 3000:
        opening = random.choice([
            f"「{機種名}」は、現状のデータから見て非常に優れた運用成果を上げており、今後の中核機種候補といえます。",
            f"「{機種名}」は、現場において注目すべき高効率機種です。"
        ])
        detail = random.choice([
            f"1日あたりの粗利が {粗利:,.0f} 円に対し、日償却額は {償却額:,.0f} 円。差し引きで +{償却効率:,.0f} 円の収益性を確保しています。",
            f"収支バランスにおいて安定感があり、現時点でも十分な利益源として機能しています。"
        ])
        suggestion = random.choice([
            "増台やイベントでの優遇配置を検討することで、更なる集客・収益増加が見込めます。",
            "運用戦略の柱として、より長期的な活用も選択肢に入るでしょう。",
            "より積極的な訴求・稼働強化を検討するフェーズにあります。"
        ])
        return f"{opening}\n{detail}\n{suggestion}"

    elif 償却効率 < 0:
        opening = random.choice([
            f"「{機種名}」については、現在の償却バランスに課題が見られます。",
            f"「{機種名}」は、収益性においてやや不安定な状況にあります。"
        ])
        detail = random.choice([
            f"粗利 {粗利:,.0f} 円に対し、償却額 {償却額:,.0f} 円を下回っており、差額は {償却効率:,.0f} 円のマイナスです。",
            f"現行の運用スタイルでは、継続的な赤字状態が想定されます。"
        ])
        suggestion = random.choice([
            "早期の撤去や構成見直しを含めた再検討を推奨します。",
            "稼働が伴わない場合、機種のリストラも含めた判断が求められます。",
            "機種構成のスリム化や、他機種への投資転換を視野に入れるべきかもしれません。"
        ])
        return f"{opening}\n{detail}\n{suggestion}"

    else:
        return ""
    

# --- 自社ホールの分析ページ用CSVを動的に読み込み ---
df_store = load_csv(get_store_file("5pachi_geocode.csv"), encoding="shift_jis")
df_town = load_csv(get_store_file("miyazaki_city_with_latlon.csv"), encoding="utf-8")
#df_town = load_csv(get_store_file("city_with_latlon.csv"), encoding="utf-8")
#df_sales = load_csv(get_store_file("sales_weather.csv"), encoding="utf-8", parse_dates=["日付"])
#df_customers = load_csv(get_store_file("hourly_customers.csv"), encoding="utf-8-sig", parse_dates=["日付"])



# --- 各ページの内容 ---
# ページ1：自社ホールの分析
if st.session_state.selected_page == "自社ホールの分析":
    #store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")
    st.title("🏪 自社ホールの分析")
    st.write("ここに自社ホールの統計情報などを表示")


    # ----------------------
    # 店舗（顧客専用）
    filtered_store = df_store[df_store["ホール名"] == selected_store]
    if filtered_store.empty:
        st.error(f"❌ 「{selected_store}」はデータに存在しません。")
        st.stop()
    store_data = filtered_store.iloc[0]
    store_lat, store_lon = store_data["緯度"], store_data["経度"]
    P = store_data["P台数"]
    S = store_data["S台数"]
    total = P + S


    # ----------------------
    # 店舗ランク（仮ルール）
    if total >= 600:
        rank = "大型"
    elif total >= 400:
        rank = "中型"
    else:
        rank = "小型"


    # ----------------------
    # 商圏人口（緯度経度から半径5km圏内）
    df_town = pd.read_csv("./data/miyazaki_city_with_latlon.csv", encoding="utf-8")
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = map(math.radians, (lat1, lat2))
        dphi = math.radians(lat2 - lat1)
        dlmb = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    df_town["dist_km"] = df_town.apply(lambda x: haversine(store_lat, store_lon, x["latitude"], x["longitude"]), axis=1)
    area_population = 0.1*(df_town[df_town["dist_km"] <= 5]["population"].sum())  # 5km圏


    # ----------------------
    # セクション①：サマリーカード
    st.markdown("## あなたのホールの概要", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(" P台数", P)
    col2.metric(" S台数", S)
    col3.metric(" 店舗ランク", rank)
    col4.metric(" 商圏人口（5km圏）", f"{int(area_population):,}人")


    # セクション①.5：構成比グラフ（P台数 vs S台数）
    st.markdown("##  遊技機構成バランス", unsafe_allow_html=True)


    df = pd.DataFrame({
        "項目": ["P台数", "S台数"],
        "値": [P, S]
    })


    chart = alt.Chart(df).mark_bar(
        color='#a88838',
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4
    ).encode(
        x=alt.X("項目:N", axis=alt.Axis(labelColor='#2f2f2f', title='')),
        y=alt.Y("値:Q", axis=alt.Axis(labelColor='#2f2f2f', title='台数')),
        tooltip=["項目", "値"]
    ).properties(
        width=400,
        height=300,
        background='#f7f5f0',
        title="P / S 台数構成"
    ).configure_title(
        font='Yu Mincho',
        fontSize=18,
        color='#333'
    ).configure_view(
        stroke=None  # 外枠をなくして柔らかく
    )


    st.altair_chart(chart, use_container_width=False)




    # ----------------------
    # セクション②：自店と競合のバブルマップ
    st.markdown("## 店舗配置と周辺競合")
    import folium
    from streamlit_folium import folium_static
    m = folium.Map(location=[store_lat, store_lon], zoom_start=13)
    folium.CircleMarker(location=[store_lat, store_lon], radius=12, color="red", fill=True, tooltip="あなたの店舗").add_to(m)
    for _, row in df_store.iterrows():
        if row["ホール名"] != selected_store:
            folium.CircleMarker(location=[row["緯度"], row["経度"]], radius=8, color="blue", fill=True, tooltip=row["ホール名"]).add_to(m)
    folium_static(m)


    # ----------------------
    # セクション④：商圏シェア（Huff）
    st.markdown("##  商圏シェア率")
    alpha = 1.5
    time_factors = {8: 0.7, 12: 0.93, 18: 0.8}
    weather_factor = 0.8
    hour = 12
    pop_factor = time_factors[hour] * weather_factor
    pop_dyn = df_town["population"] * pop_factor
    pop_sum = pop_dyn.sum()


    shares = []
    for store in df_store.itertuples():
        dists = df_town.apply(lambda t: haversine(t["latitude"], t["longitude"], store.緯度, store.経度) + 1e-6, axis=1)
        weights = (store.P台数 + store.S台数) / (dists ** alpha)
        pij = weights / weights.sum()
        share = (pop_dyn * pij).sum() / pop_sum
        shares.append(share)
    df_store["share"] = shares
    target_share = df_store[df_store["ホール名"] == selected_store]["share"].values[0]

        # --- ★平均売上単価の算出（merged_sales_weather + hourly_customers_long）
    try:
        df_sales = pd.read_csv(get_store_file("merged_sales_weather.csv"), encoding="utf-8", parse_dates=["日付"])
        df_customers = pd.read_csv(get_store_file("hourly_customers_long.csv"), encoding="utf-8-sig", parse_dates=["日付"])
        df_total = df_customers.groupby("日付")["客数"].sum().reset_index()
        if df_merged.empty:
            st.warning("この店舗には対応するデータがないため、このページは表示できません。")
            st.stop()
        df_merged = pd.merge(df_sales, df_total, on="日付", how="inner")
        df_merged["売上単価"] = df_merged["台売上合計"] / df_merged["客数"]
        avg_sales_per_person = df_merged["売上単価"].mean()
    except Exception as e:
        st.error("売上単価データの読み込みに失敗。仮に8000円を使用します。")
        avg_sales_per_person = 8000

    st.markdown("###  機種構成シミュレーション")
    adjusted_P = st.slider("P台数（調整後）", 0, 600, value=P, step=10)
    adjusted_S = st.slider("S台数（調整後）", 0, 600, value=S, step=10)

    df_store_sim = df_store.copy()
    df_store_sim.loc[df_store_sim["ホール名"] == selected_store, "P台数"] = adjusted_P
    df_store_sim.loc[df_store_sim["ホール名"] == selected_store, "S台数"] = adjusted_S

    shares_improved = []
    for store in df_store_sim.itertuples():
        dists = df_town.apply(lambda t: haversine(t["latitude"], t["longitude"], store.緯度, store.経度) + 1e-6, axis=1)
        weights = (store.P台数 + store.S台数) / (dists ** alpha)
        pij = weights / weights.sum()
        share = (pop_dyn * pij).sum() / pop_sum
        shares_improved.append(share)
    df_store_sim["share"] = shares_improved
    adjusted_share = df_store_sim[df_store_sim["ホール名"] == selected_store]["share"].values[0]

    adjusted_value = adjusted_share * 1.25 * 100
    adjusted_delta = adjusted_value - (target_share * 100)
    share_diff = adjusted_delta / 100
    additional_visitors = int(area_population * share_diff)
    revenue_gain = int(additional_visitors * avg_sales_per_person)

    st.markdown("### 商圏シェアと売上インパクト")
    col1, col2 = st.columns(2)
    col1.metric("現状シェア", f"{target_share*100:.2f}%")
    col2.metric("構成変更後シェア", f"{adjusted_value:.2f}%", delta=f"{adjusted_delta:+.2f}%")

    st.markdown("### 予測インパクト換算（実データベース）")
    st.markdown(f"""
    - **想定追加来店者数**：<span style="color:#a88838; font-weight:bold">{additional_visitors:,}人</span>  
    - **想定追加売上（1人あたり¥{int(avg_sales_per_person):,}）**：<span style="color:#a88838; font-weight:bold">¥{revenue_gain:,}</span>
    """, unsafe_allow_html=True)



    # 改善後のシェア取得
    improved_share = df_store_sim[df_store_sim["ホール名"] == selected_store]["share"].values[0]




    #  表示ブロック（高級風）
    st.markdown("###  商圏シェア改善予測", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    col1.metric("現状シェア", f"{target_share*100:.2f}%")
        # 表示用値（1.25倍補正して%表示）
    adjusted_value = improved_share * 1.25 * 100
    # 差分（補正後の値と現状%の差）
    adjusted_delta = adjusted_value - (target_share * 100)


    col2.metric(
        "改善後予測",
        f"{adjusted_value:.2f}%",
        delta=f"{adjusted_delta:+.2f}%",
        delta_color="normal"
)
    #  パラメータ（仮置き・後で調整可）
    avg_sales_per_person = 8000  # 1人あたり売上
    population = area_population  # 商圏人口（5km圏）


    #  差分計算（すでに補正された share を使う）
    adjusted_value = improved_share * 1.25 * 100
    adjusted_delta = adjusted_value - (target_share * 100)
    share_diff = (adjusted_delta) / 100  # パーセント表記を小数に戻す


    #  来店者数インパクト
    additional_visitors = int(population * share_diff)


    #  売上インパクト
    revenue_gain = int(additional_visitors * avg_sales_per_person)


    #  表示
    st.markdown("###  予測インパクト換算", unsafe_allow_html=True)


    st.markdown(f"""
    -  **想定追加来店者数**：<span style="color:#a88838; font-weight:bold">{additional_visitors:,}人</span>  
    -  **想定追加売上**：<span style="color:#a88838; font-weight:bold">¥{revenue_gain:,}</span>
    """, unsafe_allow_html=True)


    # セクション⑤：AIによる自然文提案（adjusted構成に対応）
    st.markdown("##  AIからの改善アドバイス")

    # 地域平均
    avg_P = int(df_store["P台数"].mean())
    avg_S = int(df_store["S台数"].mean())
    avg_total = int(df_store["P台数"].mean() + df_store["S台数"].mean())

    # 現在の構成（スライダーで調整後の値）
    total = adjusted_P + adjusted_S

    # ① P台数が少ない → 拡張提案
    if adjusted_P < avg_P - 20:
        st.info(
            f"""
            P台数が地域平均（{avg_P}台）より少なく、集客ポテンシャルを活かしきれていない可能性があります。

            **提案**：P台数を +20〜+40 台増やすことで、Huffモデル上の来店確率が上昇し、商圏シェアが拡大する余地があります。
            """
        )

    # ② S台数が多い → 機構成最適化提案
    elif adjusted_S > avg_S + 20:
        st.warning(
            f"""
            S台数が地域平均（{avg_S}台）より多く、稼働率が低下している恐れがあります。

            **提案**：S台数を -30〜-50 台調整し、人気機種中心のラインナップに最適化することで、1台あたりの売上効率が向上する可能性があります。
            """
        )

    # ③ P+S が平均より小さい → 拡張＋広告提案
    elif total < avg_total - 50:
        st.info(
            f"""
            総設置台数（{total}台）が地域平均（{avg_total}台）より少なく、商圏内での存在感が弱まっている可能性があります。

            **提案**：一部フロア拡張 or 強化訴求（折込・LINE）により来店数の底上げを狙えます。
            """
        )

    # ④ 規模は大きいがS偏重 →バランス是正提案
    elif adjusted_P > 400 and adjusted_S > 250:
        st.warning(
            f"""
            ⚠️ PとSがともに多く、特にS構成がやや過剰な傾向です。

            **提案**：S台数を -10〜-20台調整し、P台優遇型構成に寄せると、ピーク時間帯の稼働率改善に繋がる可能性があります。
            """
        )

    # ⑤ バランス良好 → 現状維持＋微改善
    else:
        st.success(
            f"""
            現在の構成（P={adjusted_P}, S={adjusted_S}）は地域と比較してバランス良好です。

            **提案**：この状態を維持しつつ、日替わりイベントやSNS施策による微改善を狙いましょう。
            """
        )

# ページ6：月別売上目標と予測
elif st.session_state.selected_page == "月別売上目標ダッシュボード":
    #store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("📆 月別売上目標ダッシュボード")

    import pandas as pd
    import numpy as np
    import joblib
    from datetime import datetime, timedelta

    # モデル・データ読み込み
    model = load_pkl(model_paths["weather"])
    df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])
    df["日付"] = df["日付"].dt.date

    # 今月の1日〜末日までの日付を生成
    today = datetime.today()
    first_day_this_month = today.replace(day=1)
    last_day_this_month = (first_day_this_month + pd.DateOffset(months=1)) - timedelta(days=1)
    forecast_dates = pd.date_range(start=first_day_this_month, end=last_day_this_month).date
    df_forecast = pd.DataFrame({"日付": forecast_dates})

    # 特徴量テンプレート作成（平均値ベース）
    feature_cols = [col for col in df.columns if col not in ["日付", "売上", "台売上合計"]]
    numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    feature_template = df[numeric_cols].mean()
    X = pd.DataFrame([feature_template.copy() for _ in range(len(df_forecast))])
    X.reset_index(drop=True, inplace=True)

    # 特徴量整形：不足分は0補完、順序はモデルに合わせる
    model_features = model.feature_names_in_ if hasattr(model, "feature_names_in_") else X.columns
    for col in model_features:
        if col not in X.columns:
            X[col] = 0
    X = X[model_features]

    # 売上予測実行
    df_forecast["予測売上"] = model.predict(X).astype(int)
    df_forecast["年月"] = pd.to_datetime(df_forecast["日付"]).dt.strftime("%Y-%m")

    # 月別集計
    monthly_result = df_forecast.groupby("年月")["予測売上"].sum().reset_index()

    # 結果表示
    st.markdown("### 🔮 月別売上予測")
    st.dataframe(monthly_result)

    st.markdown("### 🎯 目標売上の設定と比較")
    for _, row in monthly_result.iterrows():
        month_str = row["年月"]
        forecast = row["予測売上"]

        target = st.number_input(
            f"{month_str} の目標売上（円）",
            min_value=0,
            key=f"target_{month_str}"
        )

        achieved = forecast >= target

        # 達成率（達成率 = 予測 / 目標）
        #ratio = forecast / target * 100 if target > 0 else 0

        # 差額の中身とラベルを分岐
        if achieved:
            label = "今月目標まで残り"
            gap = abs (target - forecast)  # 顧客にとって余っている金額
        else:
            label = "今月の目標余剰金額"
            gap = abs (forecast - target)  # 未達成額（マイナスになる）

        # 表示
        col1, col2 = st.columns(2)
        col1.metric("予測売上", f"{forecast:,} 円")
        col2.metric(
            label,
            f"{gap:+,} 円",
            #delta=f"{ratio:.1f}%",
            delta_color="normal" if achieved else "inverse"
        )

        # 中央に達成判定
        st.markdown(" ")
        col_center = st.columns(3)[1]
        with col_center:
            if achieved:
                st.error("⚠️ 未達")
            else:
                st.success("✅ 達成")






# ページ6：月別売上目標と予測
elif st.session_state.selected_page == "月別売上目標ダッシュボード":
    #store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("📆 月別売上目標ダッシュボード")

    import pandas as pd
    import numpy as np
    import joblib
    from datetime import datetime, timedelta

    # モデル・データ読み込み
    model = load_pkl(model_paths["weather"])
    df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])
    df["日付"] = df["日付"].dt.date

    # 今月の1日〜末日までの日付を生成
    today = datetime.today()
    first_day_this_month = today.replace(day=1)
    last_day_this_month = (first_day_this_month + pd.DateOffset(months=1)) - timedelta(days=1)
    forecast_dates = pd.date_range(start=first_day_this_month, end=last_day_this_month).date
    df_forecast = pd.DataFrame({"日付": forecast_dates})

    # 特徴量テンプレート作成（平均値ベース）
    feature_cols = [col for col in df.columns if col not in ["日付", "売上", "台売上合計"]]
    numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    feature_template = df[numeric_cols].mean()
    X = pd.DataFrame([feature_template.copy() for _ in range(len(df_forecast))])
    X.reset_index(drop=True, inplace=True)

    # 特徴量整形：不足分は0補完、順序はモデルに合わせる
    model_features = model.feature_names_in_ if hasattr(model, "feature_names_in_") else X.columns
    for col in model_features:
        if col not in X.columns:
            X[col] = 0
    X = X[model_features]

    # 売上予測実行
    df_forecast["予測売上"] = model.predict(X).astype(int)
    df_forecast["年月"] = pd.to_datetime(df_forecast["日付"]).dt.strftime("%Y-%m")

    # 月別集計
    monthly_result = df_forecast.groupby("年月")["予測売上"].sum().reset_index()

    # 結果表示
    st.markdown("### 🔮 月別売上予測")
    st.dataframe(monthly_result)

    st.markdown("### 🎯 目標売上の設定と比較")
    for _, row in monthly_result.iterrows():
        month_str = row["年月"]
        forecast = row["予測売上"]

        target = st.number_input(
            f"{month_str} の目標売上（円）",
            min_value=0,
            key=f"target_{month_str}"
        )

        achieved = forecast >= target

        # 達成率（達成率 = 予測 / 目標）
        #ratio = forecast / target * 100 if target > 0 else 0

        # 差額の中身とラベルを分岐
        if achieved:
            label = "今月目標まで残り"
            gap = abs (target - forecast)  # 顧客にとって余っている金額
        else:
            label = "今月の目標余剰金額"
            gap = abs (forecast - target)  # 未達成額（マイナスになる）

        # 表示
        col1, col2 = st.columns(2)
        col1.metric("予測売上", f"{forecast:,} 円")
        col2.metric(
            label,
            f"{gap:+,} 円",
            #delta=f"{ratio:.1f}%",
            delta_color="normal" if achieved else "inverse"
        )

        # 中央に達成判定
        st.markdown(" ")
        col_center = st.columns(3)[1]
        with col_center:
            if achieved:
                st.error("⚠️ 未達")
            else:
                st.success("✅ 達成")










# ページ2：売上予測シミュレーター
elif st.session_state.selected_page == "売上予測シミュレーター仮":
    #store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("📈 売上予測シミュレーター仮")
    st.write("ここに予測モデルの内容を仮実装")




    dates = pd.date_range(date.today(), periods=3)
    sales_df = pd.DataFrame({"日付": dates, "売上予測(万円)": [230, 260, 240]})
    st.altair_chart(alt.Chart(sales_df).mark_line(point=True).encode(x="日付:T", y="売上予測(万円):Q").properties(height=300), use_container_width=True)
    factors_df = pd.DataFrame({"要因": ["天候", "曜日", "競合施策"], "影響度": [0.12, -0.08, -0.05]})
    factor_chart = alt.Chart(factors_df).mark_bar(size=20).encode(x=alt.X("影響度:Q", scale=alt.Scale(domain=[-1, 1])), y=alt.Y("要因:N", sort="-x"), color=alt.Color("要因:N")).properties(height=250)
    st.altair_chart(factor_chart, use_container_width=True)


    st.altair_chart(
        alt.Chart(sales_df).mark_line(point=True).encode(
            x="日付:T",
            y="売上予測(万円):Q"
        ).properties(height=300),
        use_container_width=True
    )


    st.write("\n**要因別分析（仮データ）**")
    factors_df = pd.DataFrame({
        "要因": ["天候", "曜日", "競合施策"],
        "影響度": [0.12, -0.08, -0.05]
    })
    factor_chart = alt.Chart(factors_df).mark_bar(size=20).encode(
        x=alt.X("影響度:Q", scale=alt.Scale(domain=[-1, 1])),
        y=alt.Y("要因:N", sort="-x"),
        color=alt.Color("要因:N")
    ).properties(height=250)
    st.altair_chart(factor_chart, use_container_width=True)


# ページ2：地理マップ分析
elif st.session_state.selected_page == "地理マップ分析":
    st.title("🗺 地理マップ分析")
    st.write("ここにFoliumなどで地図を表示")

    tab1, tab2 = st.tabs(["シンプル地図", "Huffシミュレーション"])

    df_town = pd.read_csv("./data/miyazaki_city_with_latlon.csv", encoding="utf-8")
    df_raw = pd.read_csv("./data/miyazaki_5pachi_geocode.csv", encoding="shift_jis")
    df_store = pd.DataFrame({
        'name': df_raw['ホール名'],
        'size': df_raw['P台数'] + df_raw['S台数'],
        'lat': df_raw['緯度'],
        'lon': df_raw['経度']
    })


    with tab1:
        st.map(df_store.rename(columns={'lat': 'latitude', 'lon': 'longitude'}))
        st.dataframe(df_store)


    with tab2:
        st.markdown("### Huffモデルを用いたシェア・来店予測")
        alpha = st.slider("距離減衰係数 α", 1.0, 3.0, 1.5, step=0.1)
        hour = st.selectbox("時間帯", [8, 12, 18], index=1)
        weather_factor = st.slider("天候ファクター", 0.4, 1.0, 0.8, step=0.1)


        time_factors = {8: 0.7, 12: 0.93, 18: 0.8}
        pop_factor = time_factors.get(hour, 1.0) * weather_factor
        pop_dyn = df_town['population'] * pop_factor
        pop_sum = pop_dyn.sum()


        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            phi1, phi2 = map(math.radians, (lat1, lat2))
            dphi = math.radians(lat2 - lat1)
            dlmb = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
            return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


        shares = []
        for store in df_store.itertuples():
            dists = df_town.apply(lambda t: haversine(t['latitude'], t['longitude'], store.lat, store.lon) + 1e-6, axis=1)
            weights = store.size / (dists ** alpha)
            pij = weights / weights.sum()
            share = (pop_dyn * pij).sum() / pop_sum
            shares.append(share)


        df_store['share'] = shares
        max_share = max(shares)


        st.subheader(" 店舗シェア一覧")
        st.dataframe(df_store[['name', 'share']].sort_values('share', ascending=False))


        st.subheader(" シェア棒グラフ")
        share_chart = alt.Chart(df_store).mark_bar(size=10).encode(
            x=alt.X("share:Q", scale=alt.Scale(domain=[0, max_share])),
            y=alt.Y("name:N", sort="-x"),
            color=alt.Color("name:N")
        ).properties(height=600)
        st.altair_chart(share_chart, use_container_width=True)


        st.subheader(" ヒートマップ（来店予測）")
        visits_pred = []
        for _, town in df_town.iterrows():
            dists = df_store.apply(lambda s: haversine(town['latitude'], town['longitude'], s.lat, s.lon) + 1e-6, axis=1)
            weights = df_store['size'] / (dists ** alpha)
            pij = weights / weights.sum()
            visits_pred.append((pop_dyn * pij).sum())
        df_town['visits_pred'] = visits_pred


        heat_df = df_town[['latitude', 'longitude', 'visits_pred']].dropna()
        m1 = folium.Map(location=[df_town['latitude'].mean(), df_town['longitude'].mean()], zoom_start=12)
        HeatMap(heat_df.values.tolist(), radius=20).add_to(m1)
        folium_static(m1, width=800, height=450)


        st.subheader(" バブルマップ（店舗シェア）")
        m2 = folium.Map(location=[df_town['latitude'].mean(), df_town['longitude'].mean()], zoom_start=12)
        for store in df_store.itertuples():
            r = (store.share / max_share) * 300
            folium.Circle(location=[store.lat, store.lon], radius=r, fill=True, fill_opacity=0.6).add_to(m2)
        folium_static(m2, width=800, height=450)


# ページ3：ホール内ランキング

elif st.session_state.selected_page == "ホール内ランキング":
    #store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("ホール内ランキング(全店舗契約特典)")
    st.write("ホール内のランキング情報を表示")

    stores_df = pd.DataFrame({
        "拠点": ["A店", "B店", "C店"],
        "売上予測(万円)": [250, 195, 180],
        "差分": ["+4%", "-8%", "+6%"],
        "主な要因": ["曜日", "雨×競合", "天候"]
    })
    st.dataframe(stores_df)


# ページ4：時系列シナリオ分析
# elif menu == "時系列シナリオ分析":
#     st.subheader("売上の時系列シナリオ分析")


#     timeline = pd.date_range(start="2024-01-01", periods=12, freq="M")
#     sales_series = pd.DataFrame({"月": timeline, "売上(万円)": [220, 210, 230, 250, 270, 260, 255, 245, 240, 250, 265, 275]})


#     st.line_chart(sales_series.rename(columns={"月": "index"}).set_index("index"))


# ページ5：売上予測シミュレーター
# # ページ5：売上予測シミュレーター
# elif st.session_state.selected_page == "売上予測シミュレーター":
#     st.title("売上予測シミュレーター")
#     st.write("XGBoostモデル")

#     import joblib
#     import shap
#     import matplotlib.pyplot as plt
#     import pandas as pd
#     import numpy as np
#     from datetime import timedelta
#     model_weather = load_pkl(model_paths["weather"])
#     explainer = shap.Explainer(model_weather)
#     model_hit = load_pkl(model_paths["hit"])
#     model_profit = load_pkl(model_paths["profit"])
#     model_sales = load_pkl(model_paths["sales"])
#     model_base = load_pkl(model_paths["base"])


#     df = pd.read_csv("merged_sales_weather.csv", parse_dates=["日付"])
#     df["日付"] = pd.to_datetime(df["日付"]).dt.date

#     start_date = st.date_input("予測開始日")
#     forecast_days = st.slider("予測日数（最大30日）", 1, 30, 7)

#     forecast_dates = pd.date_range(start=start_date, periods=forecast_days).date
#     df_forecast = pd.DataFrame({"日付": forecast_dates})

#     if df_forecast.empty:
#         st.warning("指定された日付範囲に該当するデータが見つかりませんでした。")
#     else:
#         feature_cols = [col for col in df.columns if col not in ["日付", "売上"]]

#         # 数値列のみ平均でテンプレート作成
#         numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
#         feature_template = df[numeric_cols].mean()

#         X = pd.DataFrame([feature_template.copy() for _ in range(len(df_forecast))])
#         X.reset_index(drop=True, inplace=True)

#         # 打込・台粗利・台売上を個別モデルで予測して補完
#         hit_X = df[model_hit.feature_names_in_].iloc[0:len(df_forecast)].copy()
#         profit_X = df[model_profit.feature_names_in_].iloc[0:len(df_forecast)].copy()
#         sales_X = df[model_sales.feature_names_in_].iloc[0:len(df_forecast)].copy()

#         for mX in [hit_X, profit_X, sales_X]:
#             for col in mX.select_dtypes(include='object').columns:
#                 mX[col] = pd.factorize(mX[col])[0]

#         X["打込"] = model_hit.predict(hit_X)
#         X["台粗利"] = model_profit.predict(profit_X)
#         X["台売上"] = model_sales.predict(sales_X)

#         # 特徴量整形
#         model_features = model.feature_names_in_ if hasattr(model, "feature_names_in_") else X.columns
#         missing_cols = [col for col in model_features if col not in X.columns]
#         for col in missing_cols:
#             X[col] = 0
#         X = X[model_features]

#         y_pred = model.predict(X)
#         df_result = df_forecast[["日付"]].copy()
#         df_result["予測売上"] = y_pred.astype(int)

#         st.markdown("#### 予測売上一覧")
#         st.dataframe(df_result)
#         st.line_chart(df_result.set_index("日付"))

#         st.markdown("#### 特徴量の平均SHAP重要度")
#         shap_values_all = explainer(X)
#         mean_shap = abs(shap_values_all.values).mean(axis=0)
#         shap_df = pd.DataFrame({"特徴量": X.columns, "平均重要度": mean_shap})
#         st.bar_chart(shap_df.set_index("特徴量"))

#         st.markdown("#### 売上上位3日の要因分析 (SHAP)")
#         top3 = df_result.sort_values("予測売上", ascending=False).head(3)
#         for row in top3.itertuples():
#             idx = df_forecast[df_forecast["日付"] == row.日付].index[0]
#             shap_values = explainer(X.iloc[[idx]])
#             st.markdown(f"**{row.日付.strftime('%Y-%m-%d')} のSHAP要因**")
#             fig = plt.figure()
#             shap.plots.waterfall(shap_values[0], show=False)
#             st.pyplot(fig)
#             plt.clf()






# #仮ページ
# elif st.session_state.selected_page == "売上予測シミュレーター（最適化）":
#     store_name = st.session_state.get("store_name", "店舗名未設定")
#     st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

#     st.title("🎯 売上予測シミュレーター（最適化モデル）")

#     import joblib
#     import pandas as pd
#     from datetime import date

#     try:
#         model = load_pkl(model_paths["weather"])

#     except Exception as e:
#         st.error("❌ モデルの読み込みに失敗しました")
#         st.exception(e)
#         st.stop()

#     # 入力欄
#     target_date = st.date_input("予測日", value=date.today())
#     weekday = target_date.weekday()
#     hour = st.selectbox("時間帯", [8, 12, 18], index=1)

#     store = st.selectbox("店舗", ["A店", "B店", "C店"])
#     p_table = {"A店": 400, "B店": 300, "C店": 350}
#     s_table = {"A店": 200, "B店": 150, "C店": 180}
#     P = p_table[store]
#     S = s_table[store]

#     if st.button("売上を予測する"):
#         try:
#             X_input = pd.DataFrame([[weekday, hour, P, S]],
#                 columns=["曜日_x", "時間帯", "P台数", "S台数"])  # モデルの特徴量に合わせて変更
#             y_pred = model.predict(X_input)[0]
#             st.success(f"📅 {target_date} の予測売上：¥{int(y_pred):,} 円")
#         except Exception as e:
#             st.error("❌ 予測実行中にエラーが発生しました")
#             st.exception(e)







# ページ6：売上予測シミュレーター（What-if分析)
# --- タイトル・初期情報 ---
elif st.session_state.selected_page == "What-ifシナリオシミュレーター":
    store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### \U0001f3e2 現在ログイン中の店舗：**{store_name}**")

    st.title("What-if分析")
    st.write("台数変更や施策を変えた場合のシミュレーション")

    # --- 店舗ごとのモデル読み込み ---
    store_folder_map = {
        "オーパス宮崎本店": "miyazaki",
        "オーパス小松": "komatsudai",
        "オーパス都城店": "miyakonojo"
    }
    store_folder = store_folder_map.get(store_name, "miyazaki")
    model_path = f"store_data/{store_folder}/model_weather.pkl"

    try:
        model = joblib.load(model_path)
        explainer = shap.Explainer(model)
    except Exception as e:
        st.error(f"モデル読み込みに失敗しました: {e}")
        st.stop()

    # --- 入力UI ---
    date_selected = st.date_input("分析日")
    #hour = st.selectbox("時間帯", [8, 12, 18], index=1)
    weekday = date_selected.weekday()

    st.markdown("外部環境項目（天候・顧客特性など）")
    出玉率 = st.slider("出玉率（%）", 85.0, 105.0, 94.0, step=0.1)
    客滞率 = st.slider("客滞率（%）", 130.0, 200.0, 165.0, step=0.1)
    平均気温 = st.slider("平均気温 (℃)", -5.0, 40.0, 18.0, step=0.5)
    最高気温 = st.slider("最高気温 (℃)", -5.0, 45.0, 25.0, step=0.5)
    最低気温 = st.slider("最低気温 (℃)", -10.0, 30.0, 12.0, step=0.5)
    日照時間 = st.slider("日照時間 (h)", 0.0, 15.0, 8.0, step=0.5)
    平均気圧 = st.slider("平均気圧 (hPa)", 990.0, 1040.0, 1010.0, step=0.5)
    最大風速 = st.slider("最大風速 (m/s)", 0.0, 40.0, 10.0, step=0.5)
    最大瞬間風速 = st.slider("最大瞬間風速 (m/s)", 0.0, 50.0, 15.0, step=0.5)
    平均風速 = st.slider("平均風速 (m/s)", 0.0, 20.0, 5.0, step=0.5)
    降水量 = st.slider("降水量 (mm)", 0.0, 200.0, 0.0, step=1.0)
    打込 = st.slider("打込 (総投入数)", 0.0, 20000.0, 8000.0, step=100.0)

    st.markdown("条件比較シナリオ(過去２年内に同店舗内で台数の上下がない場合は機能しません)")
    base_P = st.slider("ベースP台数", 100, 600, 400, step=10)
    base_S = st.slider("ベースS台数", 50, 300, 200, step=10)
    delta_P = st.slider("P台数の増減シナリオ", -100, 100, 0, step=10)
    delta_S = st.slider("S台数の増減シナリオ", -100, 100, 0, step=10)
    P1, S1 = base_P, base_S
    P2, S2 = base_P + delta_P, base_S + delta_S

    def make_input(P, S):
        return pd.DataFrame([{
            "曜日_x": weekday,
            "打込": 打込,
            "出玉率": 出玉率,
            "客滞率": 客滞率,
            "台数": P + S,
            "平均気温": 平均気温,
            "最高気温": 最高気温,
            "最低気温": 最低気温,
            "日照時間": 日照時間,
            "平均気圧": 平均気圧,
            "最大風速": 最大風速,
            "最大瞬間風速": 最大瞬間風速,
            "平均風速": 平均風速,
            "降水量": 降水量
        }])

    def prepare_input(df):
        for col in model.feature_names_:
            if col not in df.columns:
                df[col] = 0
        df = df[model.feature_names_]
        for col in df.select_dtypes(include=["object"]):
            df[col] = pd.factorize(df[col])[0]
        return df

    # --- ベース値保存機構 ---
    if "X_base_saved" not in st.session_state:
        st.session_state.X_base_saved = None

    if st.button("この設定をベースとして保存"):
        st.session_state.X_base_saved = make_input(P1, S1)
        st.success("ベース入力を保存しました。")

    if st.session_state.X_base_saved is not None:
        X_base = prepare_input(st.session_state.X_base_saved)
        pred_base = model.predict(X_base)[0]
    else:
        st.warning("ベース設定を保存してください（上のボタンを押す）")
        pred_base = None

    X_scenario = prepare_input(make_input(P2, S2))
    pred_scenario = model.predict(X_scenario)[0]

    if pred_base is not None:
        st.success(f"ベース予測：¥{int(pred_base):,} → シナリオ予測：¥{int(pred_scenario):,} 円")

    st.markdown("#### SHAP要因比較 (シナリオ側)")
    shap_values = explainer(X_scenario)
    fig = plt.figure()
    shap.plots.waterfall(shap_values[0], show=False)
    st.pyplot(fig)
    plt.clf()



# #7ページ目
# elif menu == "台数変化 vs 売上グラフ":
#     st.subheader("感応度分析：P×S 台数の変化による売上影響（実データ使用）")

#     import joblib
#     import pandas as pd
#     import plotly.graph_objs as go
#     import shap
#     import matplotlib.pyplot as plt
#     from fpdf import FPDF
#     import tempfile

#     model_sales = joblib.load("model_sales.pkl")
#     model_profit = joblib.load("model_profit.pkl")
#     explainer = shap.Explainer(model_sales)

#     # 特定日固定
#     date_selected = st.date_input("分析日")
#     weekday = date_selected.weekday()
#     hour = st.selectbox("時間帯", [8, 12, 18], index=1)

#     # 固定パラメータ（外部環境）
#     出玉率 = 94.0
#     客滞率 = 165.0
#     平均気温 = 18.0
#     最高気温 = 25.0
#     最低気温 = 12.0
#     日照時間_時間 = 8.0
#     平均現地気圧_hPa = 1010.0
#     最大風速_m_s = 10.0
#     最大風速_m_s_2 = 10.0
#     平均風速_m_s = 5.0
#     降水量 = 0.0
#     台売上合計 = 0.0
#     台粗利合計 = 0.0
#     総打込 = 8000.0
#     利益率 = 0.0
#     有効S = 0.0
#     入賞S1 = 0.0
#     BA = 0.0
#     MY = 0.0
#     玉単価 = 0.0
#     玉利 = 0.0
#     割数 = 0.0
#     勝率 = 0.0
#     景品額平均 = 0.0
#     元ファイル = 0  # 数値に変更
#     曜日_y = weekday

#     # 台数を変化させて売上予測とSHAP合計（1D）
#     model_hit = joblib.load("model_hit.pkl")
#     delta_range = range(-100, 101, 10)
#     sales_predictions = []

#     for delta in delta_range:
#         P = 400 + delta
#         S = 200 + delta
#         # 環境特徴量だけを使って打込を予測
#         hit_features = pd.DataFrame([{"曜日_x": weekday, "出玉率": 出玉率, "客滞率": 客滞率, "台数": P + S, "平均気温": 平均気温, "最高気温": 最高気温, "最低気温": 最低気温, "日照時間(時間)": 日照時間_時間, "平均現地気圧(hPa)": 平均現地気圧_hPa, "最大風速(m/s)": 最大風速_m_s, "最大風速(m/s).2": 最大風速_m_s_2, "平均風速(m/s)": 平均風速_m_s, "降水量": 降水量}])
#         総打込 = model_hit.predict(hit_features)[0]

#         input_data = pd.DataFrame([{
#             "曜日_x": weekday, "台売上合計": 台売上合計, "台粗利合計": 台粗利合計, "総打込": 総打込, "利益率": 利益率,
#             "有効S": 有効S, "入賞S1": 入賞S1, "BA": BA, "MY": MY, "出玉率": 出玉率,
#             "客滞率": 客滞率, "玉単価": 玉単価, "玉利": 玉利, "割数": 割数, "勝率": 勝率,
#             "景品額平均": 景品額平均, "台数": P + S, "元ファイル": 元ファイル, "曜日_y": 曜日_y,
#             "平均気温": 平均気温, "最高気温": 最高気温, "最低気温": 最低気温,
#             "日照時間(時間)": 日照時間_時間, "平均現地気圧(hPa)": 平均現地気圧_hPa,
#             "最大風速(m/s)": 最大風速_m_s, "最大風速(m/s).2": 最大風速_m_s_2,
#             "平均風速(m/s)": 平均風速_m_s, "降水量": 降水量
#         }])
#         y_pred = model_sales.predict(input_data)[0]
#         y_profit = model_profit.predict(input_data)[0]
#         shap_values = explainer(input_data)
#         shap_sum = shap_values.values[0].sum()
#         sales_predictions.append({
#             "P台数": P, "S台数": S,
#             "予測売上": y_pred, "予測粗利": y_profit, "SHAP合計": shap_sum
#         })

#     df_result = pd.DataFrame(sales_predictions)
#     st.line_chart(df_result.set_index("P台数")[["予測売上", "予測粗利"]])
#     st.dataframe(df_result)

#     # PDF出力
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#         pdf = FPDF()
#         pdf.add_page()
#         pdf.add_font("Noto", '', "NotoSansJP-VariableFont_wght.ttf", uni=True)
#         pdf.set_font("Noto", size=12)
#         pdf.cell(200, 10, txt="台数感応度分析レポート", ln=True)
#         pdf.ln()
#         for row in df_result.itertuples():
#             line = f"P={row.P台数}, S={row.S台数} → 売上: ¥{int(row.予測売上):,}, 粗利: ¥{int(row.予測粗利):,}"
#             pdf.cell(200, 8, txt=line, ln=True)
#         pdf.output(tmp.name)
#         with open(tmp.name, "rb") as f:
#             st.download_button("📄 PDFレポートをダウンロード", f, file_name="台数感応度レポート.pdf")

#     # 3D感応度分析
#     st.subheader("感応度分析：P×S 台数と売上の関係（Plotly 3D）")
#     delta_range_3d = range(-100, 101, 20)
#     results = []

#     for dP in delta_range_3d:
#         for dS in delta_range_3d:
#             P = 400 + dP
#             S = 200 + dS
#             # 環境特徴量で打込を予測
#             hit_features = pd.DataFrame([{"曜日_x": weekday, "出玉率": 出玉率, "客滞率": 客滞率, "台数": P + S, "平均気温": 平均気温, "最高気温": 最高気温, "最低気温": 最低気温, "日照時間(時間)": 日照時間_時間, "平均現地気圧(hPa)": 平均現地気圧_hPa, "最大風速(m/s)": 最大風速_m_s, "最大風速(m/s).2": 最大風速_m_s_2, "平均風速(m/s)": 平均風速_m_s, "降水量": 降水量}])
#             総打込 = model_hit.predict(hit_features)[0]

#             input_data = pd.DataFrame([{
#                 "曜日_x": weekday, "台売上合計": 台売上合計, "台粗利合計": 台粗利合計, "総打込": 総打込, "利益率": 利益率,
#                 "有効S": 有効S, "入賞S1": 入賞S1, "BA": BA, "MY": MY, "出玉率": 出玉率,
#                 "客滞率": 客滞率, "玉単価": 玉単価, "玉利": 玉利, "割数": 割数, "勝率": 勝率,
#                 "景品額平均": 景品額平均, "台数": P + S, "元ファイル": 元ファイル, "曜日_y": 曜日_y,
#                 "平均気温": 平均気温, "最高気温": 最高気温, "最低気温": 最低気温,
#                 "日照時間(時間)": 日照時間_時間, "平均現地気圧(hPa)": 平均現地気圧_hPa,
#                 "最大風速(m/s)": 最大風速_m_s, "最大風速(m/s).2": 最大風速_m_s_2,
#                 "平均風速(m/s)": 平均風速_m_s, "降水量": 降水量
#             }])
#             y_pred = model_sales.predict(input_data)[0]
#             results.append({"P台数": P, "S台数": S, "予測売上": y_pred})

#     df_grid = pd.DataFrame(results)
#     st.dataframe(df_grid)

#     fig = go.Figure(data=[go.Surface(
#         z=df_grid["予測売上"].values.reshape(len(delta_range_3d), len(delta_range_3d)),
#         x=df_grid["P台数"].values.reshape(len(delta_range_3d), len(delta_range_3d)),
#         y=df_grid["S台数"].values.reshape(len(delta_range_3d), len(delta_range_3d)),
#         colorscale='Viridis'
#     )])
#     fig.update_layout(
#         title="P×S感応度分析（売上予測）",
#         scene=dict(
#             xaxis_title='P台数',
#             yaxis_title='S台数',
#             zaxis_title='予測売上'
#         ),
#         margin=dict(l=0, r=0, b=0, t=40)
#     )
#     st.plotly_chart(fig, use_container_width=True)




#8ページ目
elif st.session_state.selected_page == "イベント影響分析":
    store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("イベント分析")
    st.write("イベントによる売上への影響を可視化")


    # 仮の売上データ
    sales_csv = """date,actual_sales,predicted_sales
    2025-05-01,800000,820000
    2025-05-02,750000,770000
    2025-05-03,900000,850000
    2025-05-04,700000,760000
    2025-05-05,880000,870000
    """
    df_sales = pd.read_csv(StringIO(sales_csv))
    df_sales["date"] = pd.to_datetime(df_sales["date"])


    # 仮の競合イベントデータ
    events_csv = """date,competitor_event_id,competitor_name,event_power_score
    2025-05-01,E001,店A,0.2
    2025-05-03,E002,店B,0.8
    2025-05-04,E003,店C,0.6
    """
    df_events = pd.read_csv(StringIO(events_csv))
    df_events["date"] = pd.to_datetime(df_events["date"])


    # データ結合
    df = pd.merge(df_sales, df_events, on="date", how="left")
    df = df[df["competitor_event_id"].notnull()]


    # 売上変動額の計算
    df["delta_sales"] = df["actual_sales"] - df["predicted_sales"]


    # 散布図データ
    df_scatter = df[["event_power_score", "delta_sales"]].dropna()


    # 相関・回帰分析
    slope, intercept, r_value, _, _ = linregress(df_scatter["event_power_score"], df_scatter["delta_sales"])
    x = np.linspace(0, 1, 100)
    y = slope * x + intercept


    # グラフ描画
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df_scatter["event_power_score"], df_scatter["delta_sales"], alpha=0.7)
    ax.plot(x, y, color="red", label=f"相関R={r_value:.2f}")
    ax.set_xlabel("競合イベント影響スコア (0〜1)")
    ax.set_ylabel("売上変動額（円）")
    ax.set_title("競合イベントの影響度 × 売上変動")
    ax.legend()
    st.pyplot(fig)


    # データ確認
    tab1, tab2 = st.tabs([" データ一覧", " グラフのみ"])
    with tab1:
        st.dataframe(df[["date", "competitor_name", "event_power_score", "actual_sales", "predicted_sales", "delta_sales"]])
    with tab2:
        st.pyplot(fig)


    # 説明文
    st.markdown("""
    ### このページでわかること：
    - **イベント影響スコアが高い競合イベント**ほど、売上にマイナスの影響が出ているか？を視覚的に把握できます。
    - **相関係数（R値）** によって、「どれくらい一貫した傾向があるか」も定量的に確認可能です。
    - 今後のイベント日程調整や、営業トークでの説得材料として活用できます。
    """)


# # 9ページ：影響ランキング
# elif menu == "影響ランキング":
#     st.title("イベント影響ランキング")


#         # データ読み込み関数 ここで正しいCSVファイルを組みこむ
#     def load_merged_dataframe():
#         sales_csv = """date,actual_sales,predicted_sales
#     2025-05-01,800000,820000
#     2025-05-02,750000,770000
#     2025-05-03,900000,850000
#     2025-05-04,700000,760000
#     2025-05-05,880000,870000
#     """
#         df_sales = pd.read_csv(StringIO(sales_csv))
#         df_sales["date"] = pd.to_datetime(df_sales["date"])


#         events_csv = """date,competitor_event_id,competitor_name,event_power_score
#     2025-05-01,E001,店A,0.2
#     2025-05-03,E002,店B,0.8
#     2025-05-04,E003,店C,0.6
#     """
#         df_events = pd.read_csv(StringIO(events_csv))
#         df_events["date"] = pd.to_datetime(df_events["date"])


#         df = pd.merge(df_sales, df_events, on="date", how="left")
#         df = df[df["competitor_event_id"].notnull()]
#         df["delta_sales"] = df["actual_sales"] - df["predicted_sales"]
#         return df




#     # 欠損を除外してランキング作成
#     df_filtered = df[df["delta_sales"].notnull()]
#     df_ranked = df_filtered.sort_values(by="delta_sales")


#     st.dataframe(df_ranked[["date", "competitor_name", "event_power_score", "delta_sales"]])




#     st.markdown("###  売上インパクトが大きかったイベント Top 5")
#     top5 = df_ranked.head(5)
#     st.bar_chart(top5.set_index("competitor_name")["delta_sales"])


#     st.markdown("###  売上にプラス影響を与えたイベント Top 3")
#     top3_positive = df.sort_values(by="delta_sales", ascending=False).head(3)
#     st.dataframe(top3_positive[["date", "competitor_name", "delta_sales"]])



# ページ8：天候付き売上予測
# ページ8：天候付き売上予測
elif st.session_state.selected_page == "天候付き売上予測シミュレーター":
    st.title("天候付き売上予測")
    st.write("天候データを使った売上予測のUIを実装")
    # モデル読み込み
# --- ログイン店舗からフォルダ名を取得（Streamlitセッション連携）
    store_name = st.session_state.get("store_name", "オーパス宮崎本店")
    store_folder_map = {
        "オーパス宮崎本店": "miyazaki",
        "オーパス小松": "komatsudai",
        "オーパス都城店": "miyakonojo"
    }
    store_folder = store_folder_map.get(store_name, "miyazaki")

    # --- ファイルパスを動的に構成
    csv_path = f"store_data/{store_folder}/merged_sales_weather.csv"
    model_path = f"store_data/{store_folder}/model_weather.pkl"

    # --- モデル読み込み（天候付き予測ページ用）
    try:
        model = joblib.load(model_path)
        import shap
        explainer = shap.Explainer(model)
    except:
        st.error(f"モデルファイルが見つかりません：{model_path}")
        st.stop()

    # 入力UI
    col1, col2 = st.columns(2)
    曜日_str = col1.selectbox("曜日", ["月", "火", "水", "木", "金", "土", "日"], index=0)
    曜日map = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}
    曜日 = 曜日map[曜日_str]
    月 = col2.selectbox("月", list(range(1, 13)), index=6)

    st.markdown("ホールが調整可能な項目")
    打込 = st.slider("打込", 5000, 30000, 7000, step=1)
    台数 = st.slider("設置台数", 300, 1000, 720, step=1)

    st.markdown("外部環境項目（天候・顧客特性など）")
    出玉率 = st.slider("出玉率（%）", 85.0, 105.0, 94.0, step=0.1)
    客滞率 = st.slider("客滞率（%）", 130.0, 200.0, 165.0, step=0.1)
    平均気温 = st.slider("平均気温 (℃)", -5.0, 40.0, 18.0, step=0.5)
    最高気温 = st.slider("最高気温 (℃)", -5.0, 45.0, 25.0, step=0.5)
    最低気温 = st.slider("最低気温 (℃)", -10.0, 30.0, 12.0, step=0.5)
    日照時間 = st.slider("日照時間 (h)", 0.0, 15.0, 8.0, step=0.5)
    平均気圧 = st.slider("平均気圧 (hPa)", 990.0, 1040.0, 1010.0, step=0.5)
    最大風速 = st.slider("最大風速 (m/s)", 0.0, 40.0, 10.0, step=0.5)
    最大瞬間風速 = st.slider("最大瞬間風速 (m/s)", 0.0, 50.0, 15.0, step=0.5)
    平均風速 = st.slider("平均風速 (m/s)", 0.0, 20.0, 5.0, step=0.5)
    降水量 = st.slider("降水量 (mm)", 0.0, 200.0, 0.0, step=1.0)

    if st.button("売上を予測する"):
        input_data = pd.DataFrame([{
            "曜日_x": 曜日,
            "打込": 打込,
            "出玉率": 出玉率,
            "客滞率": 客滞率,
            "台数": 台数,
            "平均気温": 平均気温,
            "最高気温": 最高気温,
            "最低気温": 最低気温,
            "日照時間": 日照時間,
            "平均気圧": 平均気圧,
            "最大風速": 最大風速,
            "最大瞬間風速": 最大瞬間風速,
            "平均風速": 平均風速,
            "降水量": 降水量
        }])

        # CatBoost用のカテゴリ変数リスト（モデル学習時と同じ）
        cat_features = ["曜日_x", "祝日フラグ", "給料日前フラグ"]

        # 対象が X または input_data のどちらか（ページごとに変わる）
        if "X" in locals():
            target_df = X
        elif "input_data" in locals():
            target_df = input_data
        else:
            raise RuntimeError("予測用データが見つかりません")

        # 型変換（重要！）＋必要な列がなければ補完
        for col in cat_features:
            if col not in target_df.columns:
                target_df[col] = "0"
            target_df[col] = target_df[col].astype(str)

        target_df["曜日_x"] = target_df["曜日_x"].astype(int)
        target_df["祝日フラグ"] = target_df["祝日フラグ"].astype(int)
        target_df["給料日前フラグ"] = target_df["給料日前フラグ"].astype(int)




        from datetime import date

        today = date.today()
        target_df["祝日フラグ"] = int(today.weekday() in [5, 6]) # 土日なら祝日扱い
        target_df["給料日前フラグ"] = int(today.day >= 25)    # 25日以降を給料日前とみなす



        # モデルの列順に揃える（超重要！）
        if hasattr(model, "feature_names_"):
            model_features = model.feature_names_
            missing_cols = [col for col in model_features if col not in target_df.columns]
            for col in missing_cols:
                target_df[col] = "0" if col in cat_features else 0
            target_df = target_df[model_features]

# 不要な列を削除
        for col in ["祝日フラグ", "給料日前フラグ"]:
            if col in target_df.columns:
                target_df = target_df.drop(columns=[col])





        pred = model.predict(target_df)[0]
        st.success(f"予測売上：¥{int(pred):,} 円")

        st.markdown("要因分析（SHAP）")
        try:
            shap_values = explainer(target_df)
            fig = plt.figure()
            shap.plots.waterfall(shap_values[0], show=False)
            st.pyplot(fig)
            plt.close(fig)

            st.markdown("特徴量の影響（上位5つ）")
            top_shap = pd.DataFrame({
                "特徴量": target_df.columns,
                "SHAP値": shap_values[0].values
            }).sort_values("SHAP値", key=abs, ascending=False).head(5)

            for row in top_shap.itertuples():
                impact = "増加" if row.SHAP値 > 0 else "減少"
                color = "#d9534f" if impact == "増加" else "#0275d8"
                金額 = abs(int(row.SHAP値))
                st.markdown(f"""
                <div style='background-color: #fff; border: 1px solid #ddd; border-left: 8px solid {color}; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;'>
                    <div style='font-size: 16px; font-weight: bold; color: #333;'>{row.特徴量}</div>
                    <div style='font-size: 14px; margin-top: 4px;'>売上が <span style='color:{color}; font-weight: bold;'>約 {金額:,} 円 {impact}しました</span>。</div>
                </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error("SHAPの解釈に失敗しました。")
            st.exception(e)






#11ページ
elif st.session_state.selected_page == "時間帯別客数ヒートマップ":
    st.title("客数ヒートマップ")
    st.write("曜日・時間帯別の平均客数ヒートマップを表示")

    try:
            import seaborn as sns
            import matplotlib.pyplot as plt

            # ---------- ✅ ログイン情報チェック ----------
            if "store_name" not in st.session_state:
                st.error("ログイン情報が見つかりません。ログインし直してください。")
                st.stop()

            store_name = st.session_state["store_name"]

            # ---------- ✅ 店舗名 → ファイル名マッピング ----------
            filename_map = {
                "オーパス宮崎本店": "hourly_customers_miyazaki.csv",
                "オーパス小松": "hourly_customers_komatsudai.csv",
                "オーパス都城": "hourly_customers_miyakonojo.csv",
                # 必要に応じて追加
            }

            if store_name not in filename_map:
                st.error(f"{store_name} に対応するCSVファイルが定義されていません。")
                st.stop()

            filename = filename_map[store_name]

            # ---------- ✅ CSV読み込み ----------
            df = pd.read_csv(filename, encoding="utf-8-sig", parse_dates=["datetime", "日付"])

            # ---------- ✅ 曜日列の追加 ----------
            df["曜日"] = df["日付"].dt.weekday
            df["曜日名"] = df["曜日"].map({0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"})

            # ---------- ✅ ピボット作成（時刻 × 曜日） ----------
            pivot = df.pivot_table(index="時刻", columns="曜日名", values="客数", aggfunc="mean")

            # 曜日順に並べ替え
            weekday_order = ["月", "火", "水", "木", "金", "土", "日"]
            pivot = pivot.reindex(columns=weekday_order)

            # ---------- ✅ ヒートマップ描画 ----------
            plt.figure(figsize=(10, 6))
            sns.heatmap(pivot, cmap="YlGnBu", annot=True, fmt=".0f", linewidths=0.5)
            plt.title(f"{store_name} の曜日 × 時間帯の平均客数", fontsize=14)
            plt.xlabel("曜日")
            plt.ylabel("時刻")
            plt.tight_layout()

            st.pyplot(plt.gcf())
            plt.clf()

            st.markdown("このヒートマップは、各曜日・時間帯ごとの平均客数を示しています。混雑傾向の把握やスタッフ配置、広告タイミングの検討に活用できます。")

    except Exception as e:
            st.error("データの読み込みまたは分析中にエラーが発生しました。")
            st.exception(e)





#12ページ目
# --- ページ判定 ---
elif st.session_state.selected_page == "時間帯別売上効率分析":
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd
    import os

    if "store_name" not in st.session_state:
        st.error("ログイン情報が見つかりません。ログインし直してください。")
        st.stop()

    # --- ログイン中の店舗名を取得 ---
    store_name = st.session_state["store_name"]
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    store_folder_map = {
        "オーパス宮崎本店": "miyazaki",
        "オーパス小松": "komatsudai",
        "オーパス都城": "miyakonojo"
    }
    store_folder = store_folder_map.get(store_name, "miyazaki")

    st.title("売上効率分析")
    st.write("1人あたり売上のヒートマップ分析")

    try:
        # --- ファイルパス構築 ---
        df_hourly_path = f"store_data/{store_folder}/hourly_customers_long.csv"
        df_sales_path = f"store_data/{store_folder}/merged_sales_weather.csv"

        if not os.path.exists(df_hourly_path) or not os.path.exists(df_sales_path):
            st.warning("店舗ごとのデータファイルが見つかりません。")
            st.stop()

        # --- 時間帯別客数データ読み込み（utf-8-sig想定）---
        df_hourly = pd.read_csv(df_hourly_path, encoding="utf-8-sig", parse_dates=["datetime", "日付"])

        # --- 売上データ読み込み（エンコーディング自動判定）---
        try:
            df_sales = pd.read_csv(df_sales_path, encoding="utf-8", parse_dates=["日付"])
        except UnicodeDecodeError:
            df_sales = pd.read_csv(df_sales_path, encoding="shift_jis", parse_dates=["日付"])

        # --- 総客数計算 ---
        df_total = df_hourly.groupby("日付")["客数"].sum().reset_index().rename(columns={"客数": "総客数"})

        # --- マージ処理 ---
        df = df_hourly.merge(df_total, on="日付", how="left")
        df = df.merge(df_sales[["日付", "台売上合計"]], on="日付", how="left")
        df = df.dropna(subset=["客数", "総客数", "台売上合計"])

        # --- 売上効率計算 ---
        df["時間別売上"] = df["台売上合計"] * (df["客数"] / df["総客数"])
        df["売上効率"] = df["時間別売上"] / df["客数"]
        df["曜日"] = df["日付"].dt.weekday
        df["曜日名"] = df["曜日"].map({0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"})

        # --- ピボット（曜日×時刻） ---
        pivot = df.pivot_table(index="曜日名", columns="時刻", values="売上効率", aggfunc="mean")
        pivot = pivot.reindex(["月", "火", "水", "木", "金", "土", "日"])

        # --- ヒートマップ描画 ---
        plt.figure(figsize=(14, 6))
        sns.heatmap(pivot, cmap="OrRd", annot=True, fmt=".0f", linewidths=0.5)
        plt.title("曜日 × 時間帯の売上効率（1人あたり売上）", fontsize=14)
        plt.xlabel("時刻")
        plt.ylabel("曜日")
        plt.tight_layout()
        st.pyplot(plt.gcf())
        plt.clf()

        # --- 解説文 ---
        st.markdown("""
            このヒートマップは、各時間帯ごとの売上効率（1人あたり売上）を示します。  
            混雑している時間と利益の出やすい時間の違いを把握し、施策や人員配置に活用できます。
        """)

    except Exception as e:
        st.error("売上または客数データの読み込み・分析でエラーが発生しました。")
        st.exception(e)



#13ページ目
elif st.session_state.selected_page == "機種別償却効率分析":
    store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("機種別分析(宮崎本店のみ対応)")
    st.write("機種ごとの償却効率・粗利分析を実装")

    import matplotlib.pyplot as plt
    import seaborn as sns
    import random

    # アドバイス文生成関数（ページ上部に定義しておく）
    def generate_advice(機種名, 償却効率, 粗利, 償却額):
        if 償却効率 > 3000:
            opening = random.choice([
                f"「{機種名}」は、現状のデータから見て非常に優れた運用成果を上げており、今後の中核機種候補といえます。",
                f"「{機種名}」は、現場において注目すべき高効率機種です。"
            ])
            detail = random.choice([
                f"1日あたりの粗利が {粗利:,.0f} 円に対し、日償却額は {償却額:,.0f} 円。差し引きで +{償却効率:,.0f} 円の収益性を確保しています。",
                f"収支バランスにおいて安定感があり、現時点でも十分な利益源として機能しています。"
            ])
            suggestion = random.choice([
                "増台やイベントでの優遇配置を検討することで、更なる集客・収益増加が見込めます。",
                "運用戦略の柱として、より長期的な活用も選択肢に入るでしょう。",
                "より積極的な訴求・稼働強化を検討するフェーズにあります。"
            ])
            return f"{opening}\n{detail}\n{suggestion}"
        elif 償却効率 < 0:
            opening = random.choice([
                f"「{機種名}」については、現在の償却バランスに課題が見られます。",
                f"「{機種名}」は、収益性においてやや不安定な状況にあります。"
            ])
            detail = random.choice([
                f"粗利 {粗利:,.0f} 円に対し、償却額 {償却額:,.0f} 円を下回っており、差額は {償却効率:,.0f} 円のマイナスです。",
                f"現行の運用スタイルでは、継続的な赤字状態が想定されます。"
            ])
            suggestion = random.choice([
                "早期の撤去や構成見直しを含めた再検討を推奨します。",
                "稼働が伴わない場合、機種のリストラも含めた判断が求められます。",
                "機種構成のスリム化や、他機種への投資転換を視野に入れるべきかもしれません。"
            ])
            return f"{opening}\n{detail}\n{suggestion}"
        else:
            return ""

    try:
        # Excelの読み込みとシート統合
        xls = pd.ExcelFile("2025.xlsx")
        if df_merged.empty:
            st.warning("この店舗には対応するデータがないため、このページは表示できません。")
            st.stop()
        df_merged = pd.concat(
            [xls.parse(sheet).assign(対象シート=sheet) for sheet in xls.sheet_names],
            ignore_index=True
        )

        df_merged.columns = df_merged.iloc[0].astype(str).str.strip()
        df_merged = df_merged.drop(index=0).reset_index(drop=True)

        # 抽出・変換
        df_use = df_merged[[
            "機種名", "台数", "平均単価", "金額合計", "営業日数", "台粗利", "期間台粗利"
        ]].copy()

        for col in ["台数", "平均単価", "金額合計", "営業日数", "台粗利", "期間台粗利"]:
            df_use[col] = pd.to_numeric(df_use[col], errors="coerce")

        df_use["日償却額"] = df_use["金額合計"] / df_use["営業日数"]
        df_use["償却効率"] = df_use["台粗利"] - df_use["日償却額"]
        df_sorted = df_use.dropna().sort_values("償却効率", ascending=False).reset_index(drop=True)

        top_n = st.slider("表示機種数（上位）", 5, 110, 30)

        # 償却効率ヒートマップ
        st.markdown("### 償却効率ヒートマップ")
        heat_df = df_sorted[["機種名", "償却効率"]].head(top_n).set_index("機種名")
        fig, ax = plt.subplots(figsize=(8, int(top_n * 0.35)))
        sns.heatmap(heat_df, annot=True, cmap="RdYlGn", fmt=".0f", linewidths=0.3, ax=ax)
        st.pyplot(fig)
        plt.clf()

        # 赤字候補リスト
        st.markdown("### 償却効率がマイナスの機種（撤去候補）")
        worst_df = df_sorted[df_sorted["償却効率"] < 0]
        if worst_df.empty:
            st.success("すべての機種が償却を上回る利益を出しています。")
        else:
            st.warning(f"{len(worst_df)}機種が赤字状態です。")
            st.dataframe(worst_df[["機種名", "台粗利", "日償却額", "償却効率"]].head(10))

        # 自動アドバイス（カード表示）
        st.markdown("### AIによるアドバイス")

        def render_card(row, color):
            advice = generate_advice(row.機種名, row.償却効率, row.台粗利, row.日償却額)
            st.markdown(f"""
            <div style='
                background-color: #fff;
                border: 1px solid #ddd;
                border-left: 8px solid {color};
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            '>
                <div style='font-size: 16px; font-weight: bold; color: #333; margin-bottom: 6px;'>
                    {row.機種名}
                </div>
                <div style='font-size: 14px; color: #222; line-height: 1.6; white-space: pre-wrap;'>
                    {advice}
                </div>
                <div style='margin-top: 12px;'>
                    <strong>日粗利:</strong> ¥{row.台粗利:,.0f}／
                    <strong>日償却額:</strong> ¥{row.日償却額:,.0f}／
                    <strong>償却効率:</strong> ¥{row.償却効率:,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        for row in df_sorted.head(3).itertuples():
            render_card(row, "#5cb85c")

        for row in worst_df.head(3).itertuples():
            render_card(row, "#d9534f")

    except Exception as e:
        st.error("データ処理中にエラーが発生しました。")
        st.exception(e)





# #14ページ目異常値検出
# elif menu == "異常値検出分析":
#     st.title("異常値検出ページ（±2σ）")
#     try:
#         df = pd.read_excel("異常値分析用データ.xlsx")
#         numeric_cols = [col for col in df.select_dtypes(include='number').columns if col not in ["台数"]]

#         for col in numeric_cols:
#             mu = df[col].mean()
#             sigma = df[col].std()
#             df[f"{col}_異常"] = ((df[col] < mu - 2 * sigma) | (df[col] > mu + 2 * sigma))

#         anomaly_flags = [f"{col}_異常" for col in numeric_cols]
#         df_anomalies = df[df[anomaly_flags].any(axis=1)]

#         summary = f"""
#     本レポートでは、主要な数値指標に対して標準偏差±2σの範囲を基準とした異常値検出を行った。
#     全データのうち {len(df)} 件のうち、{len(df_anomalies)} 件に異常値が確認された。
#     これは全体の約 {len(df_anomalies)/len(df)*100:.2f}% に相当し、特定の項目に極端な偏りがあることを示している。

#     とりわけ、異常値の多くは「{anomaly_flags[0].replace('_異常','')}」「{anomaly_flags[1].replace('_異常','')}」といった指標に集中しており、
#     これらは経営的・営業的に見逃せないシグナルである可能性が高い。
#     異常の内容には、通常よりも極端に高いまたは低い数値が含まれ、稼働の異常・外部イベント・構成の偏りなどの原因が考えられる。

#     このレポートは、日次の異常傾向把握や、戦略見直しの起点として極めて有効であり、
#     継続的に分析を行うことで、より安定した店舗運営と高精度な意思決定を支援するものとなる。
#     """

#         if st.button("PDFレポートを出力"):
#             pdf = FPDF()
#             pdf.add_page()
#             pdf.add_font("ArialUnicode", '', "arial.ttf", uni=True)
#             pdf.set_font("ArialUnicode", size=12)
#             pdf.multi_cell(0, 10, summary)

#             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#                 pdf.output(tmp.name)
#                 with open(tmp.name, "rb") as f:
#                     st.download_button("PDFレポートをダウンロード", f, file_name="anomaly_report.pdf")

#     except Exception as e:
#         st.error("PDF出力中にエラーが発生しました。")
#         st.exception(e)







#16ページ
elif st.session_state.selected_page == "AIコンサルアドバイス":
    store_name = st.session_state.get("store_name", "店舗名未設定")
    st.markdown(f"### 🏢 現在ログイン中の店舗：**{store_name}**")

    st.title("AIコンサルアドバイス(宮崎本店のみ対応)")
    st.write("AIによる営業改善提案を表示")

    try:
        xls = pd.ExcelFile("2025.xlsx")
        if df_merged.empty:
            st.warning("この店舗には対応するデータがないため、このページは表示できません。")
            st.stop()

        df_merged = pd.concat([
            xls.parse(sheet).assign(対象シート=sheet) for sheet in xls.sheet_names
        ], ignore_index=True)
        df_merged.columns = df_merged.iloc[0].astype(str).str.strip()
        df_merged = df_merged.drop(index=0).reset_index(drop=True)

        df_use = df_merged[["機種名", "台粗利", "金額合計", "営業日数"]].copy()
        df_use[["台粗利", "金額合計", "営業日数"]] = df_use[["台粗利", "金額合計", "営業日数"]].apply(pd.to_numeric, errors="coerce")
        df_use = df_use.dropna()
        df_use["日償却額"] = df_use["金額合計"] / df_use["営業日数"]
        df_use["償却効率"] = df_use["台粗利"] - df_use["日償却額"]

        機種一覧 = sorted(df_use["機種名"].dropna().unique().tolist())
        machine_name = st.selectbox("機種名を選択:", 機種一覧)

        selected_row = df_use[df_use["機種名"] == machine_name].iloc[0]
        償却効率 = selected_row["償却効率"]
        台粗利 = selected_row["台粗利"]
        償却額 = selected_row["日償却額"]

    except Exception as e:
        st.error("データの読み込みに失敗しました。手動で入力してください。")
        machine_name = st.text_input("機種名を入力:")
        償却効率 = st.number_input("償却効率（円）", value=0)
        台粗利 = st.number_input("台粗利（円）", value=0)
        償却額 = st.number_input("日償却額（円）", value=0)

    def generate_advice(機種名, 償却効率, 粗利, 償却額):
        if 償却効率 > 3000:
            return f"""
        「{機種名}」は、現在の運用データから見て非常に優れた成績を示しており、
        今後の主力機種としての継続配置や、戦略的な運用強化の候補として検討に値します。

        1日あたりの台粗利が {粗利:,.0f} 円に対し、日償却額は {償却額:,.0f} 円。
        差し引きで +{償却効率:,.0f} 円という高い収益性を維持していることから、
        この機種は償却を十分に超過したパフォーマンスを発揮していると評価できます。

        この水準での効率性が続く場合は、単なる維持にとどまらず、
        増台やイベントでの注力配置、広告的な訴求による稼働拡大を図ることも現実的な戦略です。
        また、他機種との比較においてもコストパフォーマンスが高く、
        商圏内での競合優位性を確保する上でも有効な施策が立てられるでしょう。
                """
        elif 償却効率 < 0:
            return f"""
        「{機種名}」は、現在の運用実績において明確な課題が見受けられます。
        台粗利が {粗利:,.0f} 円にとどまる一方で、日償却額が {償却額:,.0f} 円に達しており、
        その差額 {償却効率:,.0f} 円はマイナスとなっております。

        この状況が長期化する場合、店舗全体の収益効率に影響を与える可能性があり、
        短期的な稼働促進施策による改善が見込めない場合には、
        配置見直しや撤去、またはリニューアル機種への入替など、
        構成の再設計が求められる段階といえるでしょう。

        撤去判断を急ぐべきかどうかは、今後1週間〜10日の動向次第ですが、
        現時点では“危険水域”にあることは確かであり、定量的な評価をもとにした柔軟な判断が必要です。
                """
        else:
            return f"""
        「{機種名}」は、現在のところ安定した収益性を維持しており、
        台粗利 {粗利:,.0f} 円と日償却額 {償却額:,.0f} 円がほぼ同等の水準で推移しています。

        償却効率は +{償却効率:,.0f} 円とわずかながらの黒字ですが、
        この状態が継続する場合、台構成の中で“中立的”なポジションとして維持判断が妥当です。

        ただし、他機種の撤去や新機種導入による構成変化があった際には、
        相対的に利益貢献度が低下する恐れもあるため、
        今後の変化に応じて注視を続けるべきポジションにあるといえます。
                """

    if st.button("AIにアドバイスをもらう"):
        if machine_name:
            advice = generate_advice(machine_name, 償却効率, 台粗利, 償却額)
            st.markdown("### AIからのアドバイス")
            st.success(advice)
        else:
            st.warning("機種名を入力してください。")





elif st.session_state.selected_page == "売上予測シミュレーターvol.2":
    st.title("売上予測シミュレーターvol.2")
    st.write("Catboostモデル")

    import streamlit as st

    # pandas：データ処理用ライブラリ
    import pandas as pd

    import jpholiday

    # CatBoost：カテゴリ変数を直接扱える機械学習ライブラリ
    from catboost import CatBoostRegressor

    # timedelta：日付操作用（1週間予測に使用）
    from datetime import timedelta

    # joblib：モデル保存（今回は未使用だが読み込みには便利）
    import joblib

    # --- フラグ生成関数定義 ---
    def is_payday(date):
        if date.day == 25:
            return 1
        if date.day in [24, 23, 22] and (date + timedelta(days=1)).day == 25 and (date + timedelta(days=1)).weekday() < 5:
            return 1
        return 0

    def is_holiday(date):
        return int(jpholiday.is_holiday(date))

    def is_weekend(date):
        return int(date.weekday() >= 5)

    def is_pension_day(date):
        # 偶数月15日、休日なら前倒し
        if date.month % 2 == 0:
            if date.day == 15:
                return 1
            if date.day in [14, 13, 12] and (date + timedelta(days=1)).day == 15 and (date + timedelta(days=1)).weekday() < 5:
                return 1
    #     return 0

    # # --- Streamlitページの初期設定 ---
    # st.set_page_config(page_title="売上予測シミュレーター", layout="centered")
    # st.title("🐈 売上予測シミュレーター（CatBoostモデル）")

    # --- ✅ CSVからデータを読み込んでモデルの学習を行うブロック ---
    # CSVファイルを読み込む（前処理済のものを想定）
    # ✅ 店舗に応じたCSVファイルを動的に読み込み
    store_name = st.session_state.get("store_name", "店舗名未設定")

    store_code_map = {
        "オーパス宮崎本店": "miyazaki",
        "オーパス都城": "miyakonojo",
        "オーパス小松": "komatsudai"
    }
    store_code = store_code_map.get(store_name)
    if not store_code:
        st.error(f"{store_name} に対応する店舗コードが定義されていません。")
        st.stop()

    csv_path = f"store_data/{store_code}/merged_sales_weather.csv"
    if not os.path.exists(csv_path):
        st.error(f"CSVファイルが存在しません: {csv_path}")
        st.stop()

    try:
        df = load_csv(csv_path, encoding="utf-8", parse_dates=["日付"])
    except UnicodeDecodeError:
        df = load_csv(csv_path, encoding="shift_jis", parse_dates=["日付"])



    # 使用する列だけ抽出（列名を後で英語に変換）
    df = df[[
        "日付","曜日_x", "台数", "平均気温", "降水量", "台売上合計", "台売上", "台粗利合計", "台粗利", "打込",
        "総打込", "利益率", "有効S", "入賞S1", "BA", "MY", "出玉率", "客滞率", "玉単価", "玉利", "割数", "勝率",
        "景品額平均", "最高気温", "最低気温", "日照時間(時間)", "平均現地気圧(hPa)", "最大風速(m/s)",
        "最大風速(m/s).2", "平均風速(m/s)"
    ]].copy()

    # 列名を英語に変換
    df.columns = [
        "date","weekday", "machine_count", "avg_temp", "precipitation", "total_sales", "unit_sales",
        "total_profit", "unit_profit", "hit", "total_hit", "profit_margin", "effective_s",
        "s1_win", "ba", "my", "payout_rate", "stay_rate", "unit_ball_price", "unit_ball_profit",
        "return_ratio", "win_rate", "avg_prize_value", "max_temp", "min_temp", "sunshine_duration",
        "avg_pressure", "max_wind_speed_1", "max_wind_speed_2", "avg_wind_speed"
    ]

    # カテゴリ変数を文字列型に変換（weekdayはカテゴリとする）
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["weekday"].astype(str)

    # --- フラグ列追加 ---
    df["payday_flag"] = df["date"].apply(is_payday)
    df["holiday_flag"] = df["date"].apply(is_holiday)
    df["weekend_flag"] = df["date"].apply(is_weekend)
    df["pension_flag"] = df["date"].apply(is_pension_day)


    # 特徴量（X）と目的変数（y）に分割（必要に応じて使いたい変数に変更）
    X_train = df[["weekday", "machine_count", "avg_temp", "precipitation",
                "payday_flag", "holiday_flag", "weekend_flag", "pension_flag"]]
    y_train = df["total_sales"]  # ←例として「台売上（unit_sales）」を目的変数に

    # 学習前にNaNを含む行を除外する処理を追加
    train_data = pd.concat([X_train, y_train], axis=1).dropna()
    X_train = train_data.iloc[:, :-1]
    y_train = train_data.iloc[:, -1]

    # CatBoostモデルを構築（カテゴリ変数weekdayを指定）
    model = CatBoostRegressor(cat_features=["weekday"], iterations=300, verbose=0)

    model.fit(X_train, y_train)  # 学習開始
    explainer = shap.Explainer(model)

    # モデルを保存（あとで再利用可能）
    model.save_model("model/merged_sales_catboost.cbm")

    # --- ✅ Streamlitのインターフェース部分 ---

    # 店舗選択（P台数・S台数を決めるため）
    store = st.selectbox("店舗", ["オーパス宮崎本店", "オーパス都城", "オーパス小松"])

    # 店舗ごとのP/S台数設定（固定値だが辞書で管理）
    p_table = {"オーパス宮崎本店": 440, "オーパス都城": 480, "オーパス小松": 580}
    s_table = {"オーパス宮崎本店": 280, "オーパス都城": 522, "オーパス小松": 281}
    P = p_table[store]
    S = s_table[store]

    # ユーザー入力欄（予測対象の日付、期間、時間帯、天気）
    start_date = st.date_input("開始日")
    forecast_type = st.radio("予測期間", ["1日", "1週間","1か月(月末まで)"], horizontal=True)


    # --- ✅ ユーザーがボタンを押したときに予測を実行 ---
    if st.button("売上を予測する"):
        model = CatBoostRegressor()
        model.load_model("model/merged_sales_catboost.cbm")

        correction_factor = 0.84  # ← 実績とのズレを補正するための係数


        if forecast_type == "1日":
            target_date = pd.to_datetime(start_date)
            reference_date = target_date - timedelta(days=365)
            weekday = target_date.weekday()

            # 1年前のデータを取得
            past = df[df["date"] == reference_date]
            if not past.empty:
                temp = past["avg_temp"].values[0]
                rain = past["precipitation"].values[0]
            else:
                temp, rain = 25, 0  # デフォルト

            # 予測用の入力データ（tempとrainは仮で固定）
            X_input = pd.DataFrame([[str(weekday),P+S,temp,rain,
                                    is_payday(target_date),
                                    is_holiday(target_date),
                                    is_weekend(target_date),
                                    is_pension_day(target_date)
                                    ]],
                                columns=["weekday", "machine_count", "avg_temp", "precipitation",
                                            "payday_flag", "holiday_flag", "weekend_flag", "pension_flag"
                                            ])
            y_pred = model.predict(X_input)[0]*correction_factor # 予測値を取得
            # 結果を表示
            st.success(f"📅 {start_date} の予測売上：¥{int(y_pred):,} 円")
            # --- SHAP 可視化 ---
            st.subheader("🔍 特徴量の影響度（SHAP）")
            shap_values = explainer(X_input)
            fig, ax = plt.subplots()
            shap.plots.waterfall(shap_values[0], max_display=8, show=False)
            st.pyplot(fig)


        elif forecast_type == "1週間":
            result=[]
            for i in range(7):
                target_date=pd.to_datetime(start_date+timedelta(days=i))
                reference_date = target_date - timedelta(days=365)
                weekday = target_date.weekday()

                past = df[df["date"] == reference_date]
                if not past.empty:
                    temp = past["avg_temp"].values[0]
                    rain = past["precipitation"].values[0]
                else:
                    temp, rain = 25, 0

            
                X_input = pd.DataFrame([[
                    str(weekday), P + S,temp,rain,
                    is_payday(target_date),
                    is_holiday(target_date),
                    is_weekend(target_date),
                    is_pension_day(target_date)
                    ]],columns=["weekday", "machine_count", "avg_temp", "precipitation",
                    "payday_flag", "holiday_flag", "weekend_flag", "pension_flag"
                    ])
                
                y_pred = model.predict(X_input)[0]*correction_factor
                result.append({"日付": target_date.date(), "予測売上": int(y_pred)})

            # DataFrameでまとめて表示・可視化
            df_result = pd.DataFrame(result)
            st.dataframe(df_result)
            st.line_chart(df_result.set_index("日付"))
            # --- SHAP分析（最後の日付の入力を使用）---
            st.subheader("📈 SHAP分析（最終日）")
            shap_values = explainer(X_input)  # X_inputは直近ループで作られたもの
            fig, ax = plt.subplots()
            shap.plots.waterfall(shap_values[0], max_display=8, show=False)
            st.pyplot(fig)

            total = df_result["予測売上"].sum()
            st.success(f"📊 1週間の予測売上合計：¥{int(total):,} 円")

        elif forecast_type == "1か月(月末まで)":
            from calendar import monthrange
            year, month = start_date.year, start_date.month
            last_day = monthrange(year, month)[1]
            end_date = start_date.replace(day=last_day)

            forecast_dates = pd.date_range(start=start_date, end=end_date).date

            result = []
            for target_date in forecast_dates:
                reference_date = pd.to_datetime(target_date) - timedelta(days=365)
                weekday = target_date.weekday()

                past = df[df["date"] == reference_date]
                if not past.empty:
                    temp = past["avg_temp"].values[0]
                    rain = past["precipitation"].values[0]
                else:
                    temp, rain = 25, 0

                X_input = pd.DataFrame([[
                    str(weekday), P + S, temp, rain,
                    is_payday(target_date),
                    is_holiday(target_date),
                    is_weekend(target_date),
                    is_pension_day(target_date)
                ]], columns=[
                    "weekday", "machine_count", "avg_temp", "precipitation",
                    "payday_flag", "holiday_flag", "weekend_flag", "pension_flag"
                ])

                y_pred = model.predict(X_input)[0] * correction_factor
                result.append({"日付": target_date, "予測売上": int(y_pred)})

            df_result = pd.DataFrame(result)
            st.dataframe(df_result)
            st.line_chart(df_result.set_index("日付"))
            # --- SHAP分析（最後の日付の入力を使用）---
            st.subheader("📈 SHAP分析（最終日）")
            shap_values = explainer(X_input)  # X_inputは直近ループで作られたもの
            fig, ax = plt.subplots()
            shap.plots.waterfall(shap_values[0], max_display=8, show=False)
            st.pyplot(fig)

            total = df_result["予測売上"].sum()
            st.success(f"📅 1か月（{start_date.strftime('%Y-%m')}）の予測売上合計：¥{int(total):,} 円")

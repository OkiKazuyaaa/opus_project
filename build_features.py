import pandas as pd
import numpy as np
import jpholiday
from catboost import CatBoostRegressor
from xgboost import XGBRegressor

def build_features(df, model_hit, model_base, base_P=400, base_S=200):
    df_feat = df.copy()
    df_feat["日付"] = pd.to_datetime(df_feat["日付"])
    df_feat["曜日_x"] = df_feat["日付"].dt.strftime("%A")
    df_feat["祝日名"] = df_feat["日付"].apply(
        lambda x: jpholiday.is_holiday_name(x) if jpholiday.is_holiday(x) else "平日"
    )
    df_feat["祝日フラグ"] = df_feat["祝日名"].apply(lambda x: int(x != "平日"))
    df_feat["給料日前フラグ"] = df_feat["日付"].dt.day.isin([24, 25, 26]).astype(int)
    df_feat["月末フラグ"] = df_feat["日付"].dt.is_month_end.astype(int)
    df_feat["年金支給日前後フラグ"] = df_feat["日付"].dt.day.isin([13, 14, 15, 16, 17]).astype(int)

    df_feat["台数"] = base_P + base_S

    weather_defaults = {
        "平均気温": 18.0, "最高気温": 25.0, "最低気温": 12.0,
        "日照時間(時間)": 8.0, "平均現地気圧(hPa)": 1010.0, "降水量": 0.0
    }
    for col, default_val in weather_defaults.items():
        if col not in df_feat.columns:
            df_feat[col] = default_val

    base_inputs = df_feat.copy()

    # 🚩 モデルタイプで特徴量取得方法を分岐（model_base用）
    if isinstance(model_base, CatBoostRegressor):
        base_features = model_base.feature_names_
    elif isinstance(model_base, XGBRegressor):
        base_features = model_base.get_booster().feature_names
    else:
        raise ValueError("model_base が CatBoost でも XGBoost でもありません。")

    for col in base_features:
        if col not in base_inputs.columns:
            base_inputs[col] = 0
    base_inputs = base_inputs[base_features]

    base_preds = model_base.predict(base_inputs)
    if len(base_preds.shape) == 1:
        df_feat["出玉率"] = base_preds
        df_feat["客滞率"] = 165.0
    else:
        df_feat["出玉率"] = base_preds[:, 0]
        df_feat["客滞率"] = base_preds[:, 1]

    # 🚩 model_hitのモデルタイプに応じて特徴量取得方法を分岐
    hit_inputs = pd.DataFrame({
        "曜日_x": df_feat["曜日_x"],
        "出玉率": df_feat["出玉率"],
        "客滞率": df_feat["客滞率"],
        "台数": df_feat["台数"]
    })

    if isinstance(model_hit, CatBoostRegressor):
        hit_features = model_hit.feature_names_
    elif isinstance(model_hit, XGBRegressor):
        hit_features = model_hit.get_booster().feature_names
    else:
        raise ValueError("model_hit が CatBoost でも XGBoost でもありません。")

    for col in hit_features:
        if col not in hit_inputs.columns:
            hit_inputs[col] = 0
    hit_inputs = hit_inputs[hit_features]

    df_feat["打込"] = model_hit.predict(hit_inputs)

    required_cols = [
        "曜日_x", "祝日フラグ", "給料日前フラグ", "月末フラグ", "年金支給日前後フラグ",
        "台数", "出玉率", "客滞率", "打込",
        "平均気温", "最高気温", "最低気温", "日照時間(時間)",
        "平均現地気圧(hPa)", "降水量", "最大風速(m/s)", "平均風速(m/s)"
    ]
    for col in required_cols:
        if col not in df_feat.columns:
            df_feat[col] = 0

    return df_feat

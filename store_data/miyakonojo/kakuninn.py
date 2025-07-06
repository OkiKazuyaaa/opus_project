import joblib
model = joblib.load("model_weather.pkl")
print(model.feature_names_)

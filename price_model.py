import joblib
import pandas as pd

try:
    model = joblib.load("catboost_mixed_features.pkl")
except Exception as e:
    print(f"Ошибка загрузки модели ML: {e}")
    model = None

def predict_price_range(car: dict) -> int:
    if model is None:
        return 0

    df = pd.DataFrame([{
        "bodyType": car["bodytype"],
        "brand": car["brand"],
        "color": car["color"],
        "fuelType": car["fuel_type"],
        "model_name": car["model"],
        "vehicleTransmission": car["vehicle_transmission"],
        "drivetrains": car["drive_type"],
        "wheel": car["wheel"],
        "engineDisplacement": car["engine_displacement"],
        "enginePower": car["engine_power"],
        "mileage": car["mileage"],
        "productionDate": car["production_date"],
        "owners": car["owners"],
        "car_age": 2025 - car["production_date"]
    }])

    pred = model.predict(df)
    return int(pred.flatten()[0])

def price_to_range(price: float) -> int:
    if price <= 500_000: return 0
    if price <= 1_000_000: return 1
    if price <= 1_500_000: return 2
    if price <= 2_000_000: return 3
    if price <= 2_500_000: return 4
    if price <= 3_000_000: return 5
    if price <= 3_500_000: return 6
    if price <= 4_000_000: return 7
    if price <= 4_500_000: return 8
    if price <= 5_000_000: return 9
    return 10

def get_price_badge(fact: int, ml: int) -> str:
    if ml > fact:
        return "low"     # цена ниже рынка
    if ml == fact:
        return "good"    # цена нормальная
    return "high"        # цена выше рынка
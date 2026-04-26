import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from models import Car, Favorite, User, Session as DBSession


# Функция для получения данных из БД
def get_cars_data(db: Session, user_id: int):
    cars_for_sale = db.query(Car).all()
    df_sale = pd.DataFrame([{
        'car_id': c.car_id,
        'brand': c.brand,
        'bodyType': c.bodytype,
        'fuelType': c.fuel_type,
        'vehicleTransmission': c.vehicle_transmission,
        'color': c.color,
        'wheel': c.wheel,
        'price_range': c.price_range,
        'enginePower': float(c.engine_power) if c.engine_power else 0,
        'productionDate': c.production_date if c.production_date else 0
    } for c in cars_for_sale])

    # Машины, которые пользователь лайкнул
    liked_cars = (
        db.query(Car)
        .join(Favorite, Favorite.car_id == Car.car_id)
        .filter(Favorite.user_id == user_id)
        .all()
    )
    df_likes = pd.DataFrame([{
        'car_id': c.car_id,
        'brand': c.brand,
        'bodyType': c.bodytype,
        'fuelType': c.fuel_type,
        'vehicleTransmission': c.vehicle_transmission,
        'color': c.color,
        'wheel': c.wheel,
        'price_range': c.price_range,
        'enginePower': float(c.engine_power) if c.engine_power else 0,
        'productionDate': c.production_date if c.production_date else 0
    } for c in liked_cars])

    # Машины пользователя на продаже
    user_cars = db.query(Car).filter(Car.seller_id == user_id).all()
    df_user_sales = pd.DataFrame([{
        'car_id': c.car_id,
        'brand': c.brand,
        'bodyType': c.bodytype,
        'fuelType': c.fuel_type,
        'vehicleTransmission': c.vehicle_transmission,
        'color': c.color,
        'wheel': c.wheel,
        'price_range': c.price_range,
        'enginePower': float(c.engine_power) if c.engine_power else 0,
        'productionDate': c.production_date if c.production_date else 0
    } for c in user_cars])

    return df_sale, df_likes, df_user_sales

# обработка признаков
categorical_features = [
    'brand',
    'bodyType',
    'fuelType',
    'vehicleTransmission',
    'color',
    'wheel'
]

numeric_features = [
    'price_range',
    'enginePower',
    'productionDate'
]

weights = {
    'brand': 2.0,
    'bodyType': 1.8,
    'fuelType': 1.6,
    'price_range': 1.5,
    'enginePower': 1.2,
    'productionDate': 1.0,
    'vehicleTransmission': 0.8,
    'color': 0.5,
    'wheel': 0.3
}

def encode_cars(df, ohe, scaler):
    cat_encoded = ohe.transform(df[categorical_features])
    num_scaled = scaler.transform(df[numeric_features])
    return np.hstack([cat_encoded, num_scaled])

def apply_feature_weights(encoded_matrix, encoder, numeric_features, weights):
    ohe_feature_names = encoder.get_feature_names_out(categorical_features)
    all_feature_names = list(ohe_feature_names) + numeric_features

    feature_weights = np.ones(len(all_feature_names))
    for name, weight in weights.items():
        for i, fname in enumerate(all_feature_names):
            if fname in numeric_features:
                if fname == name:
                    feature_weights[i] = weight
            else:
                prefix = fname.split('_', 1)[0]
                if prefix == name:
                    feature_weights[i] = weight
    weighted = encoded_matrix * feature_weights
    return weighted

def get_car_recommendations(user_id: int, top_n: int = 20):
    db = DBSession()
    df_sale, df_likes, df_user_sales = get_cars_data(db, user_id)

    if df_sale.empty:
        db.close()
        return []

    # Cold start
    if df_likes.empty and df_user_sales.empty:
        # fallback: просто топ по цене / новизне
        fallback = (
            df_sale
            .sort_values(
                by=['price_range', 'productionDate'],
                ascending=[True, False]
            )
            .head(top_n)
        )
        db.close()
        return fallback['car_id'].tolist()

    # Подготовка кодировщиков
    all_cars = pd.concat(
        [df_sale, df_likes, df_user_sales],
        ignore_index=True
    )

    ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    ohe.fit(all_cars[categorical_features])

    scaler = StandardScaler()
    scaler.fit(all_cars[numeric_features])

    X_sale = encode_cars(df_sale, ohe, scaler)
    X_sale_w = apply_feature_weights(X_sale, ohe, numeric_features, weights)

    user_vectors = []

    # Если есть лайки — добавляем
    if not df_likes.empty:
        X_likes = encode_cars(df_likes, ohe, scaler)
        X_likes_w = apply_feature_weights(X_likes, ohe, numeric_features, weights)
        user_vectors.append(X_likes_w)

    # Если есть продажи — добавляем
    if not df_user_sales.empty:
        X_sales = encode_cars(df_user_sales, ohe, scaler)
        X_sales_w = apply_feature_weights(X_sales, ohe, numeric_features, weights)
        user_vectors.append(X_sales_w)


    # Профиль пользователя и его сходства
    user_profile = np.mean(np.vstack(user_vectors), axis=0)
    
    similarities = cosine_similarity([user_profile], X_sale_w)[0]
    df_sale['similarity'] = similarities

    recommendations = (
        df_sale
        .sort_values('similarity', ascending=False)
        .head(top_n)
    )

    db.close()
    return recommendations['car_id'].tolist()

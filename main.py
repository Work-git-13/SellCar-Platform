from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import price_model
import os
import shutil
from typing import Optional

from models import User, Session as DBSession, Base, engine, Car, Favorite, Brand, Model, BodyType
from auth import (
    authenticate_user, create_access_token, get_current_user, 
    get_password_hash, get_user_by_login
)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Sellcar API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CustomStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if path.endswith('.css'):
            response.headers['Content-Type'] = 'text/css'
        elif path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript'
        return response

os.makedirs("static", exist_ok=True)
os.makedirs("static/avatars", exist_ok=True)
app.mount("/static", CustomStaticFiles(directory="static"), name="static")

class UserLogin(BaseModel):
    login: str
    password: str

class UserRegister(BaseModel):
    login: str
    password: str
    first_name: str
    last_name: Optional[str] = None
    phone: str

class UserUpdate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    phone: str
    current_password: Optional[str] = None
    new_password: Optional[str] = None

class CarCreate(BaseModel):
    brand: str
    model: str
    production_date: int
    mileage: int
    engine_displacement: float      
    price: float
    description: Optional[str] = None
    bodytype: str
    color: str
    fuel_type: str
    vehicle_transmission: str
    owners: int
    drive_type: str
    wheel: str
    engine_power: int
    vin: str
    state_number: str 

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    first_name: str
    last_name: Optional[str]

def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/register", response_model=Token)
def api_register(user_data: UserRegister, db: Session = Depends(get_db)):
    if get_user_by_login(db, user_data.login):
        raise HTTPException(status_code=400, detail="Логин занят")
    if db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(status_code=400, detail="Телефон занят")

    hashed_pass = get_password_hash(user_data.password)
    db_user = User(
        login=user_data.login,
        password_hash=hashed_pass,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    access_token = create_access_token(data={"sub": user_data.login})
    token_resp = Token(access_token=access_token, token_type="bearer", user_id=db_user.user_id, first_name=db_user.first_name, last_name=db_user.last_name)
    
    response = JSONResponse(content=token_resp.dict())
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite='lax')
    return response

@app.post("/api/login", response_model=Token)
def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.login, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверные данные")
    
    access_token = create_access_token(data={"sub": user.login})
    token_resp = Token(access_token=access_token, token_type="bearer", user_id=user.user_id, first_name=user.first_name, last_name=user.last_name)
    
    response = JSONResponse(content=token_resp.dict())
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite='lax')
    return response

@app.post("/api/logout")
def logout():
    response = JSONResponse(content={"message": "ok"})
    response.delete_cookie(key="access_token")
    return response

@app.get("/api/user")
def get_user_info(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: return {"authenticated": False}
    try:
        user = get_current_user(token, db)
        if not user: return {"authenticated": False}
        return {
            "authenticated": True, "user_id": user.user_id,
            "first_name": user.first_name, "last_name": user.last_name,
            "login": user.login, "phone": user.phone, "avatar_url": user.avatar_url
        }
    except:
        return {"authenticated": False}
    
ph = PasswordHasher()

@app.put("/api/user/profile")
def update_profile(user_data: UserUpdate, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: 
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user = get_current_user(token, db)
    
    if user.phone != user_data.phone:
        existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Этот номер телефона уже занят")

    user.first_name = user_data.first_name
    user.last_name = user_data.last_name
    user.phone = user_data.phone
    
    if user_data.new_password:
        if not user_data.current_password:
            raise HTTPException(status_code=400, detail="Введите текущий пароль для смены")
        
        try:
            ph.verify(user.password_hash, user_data.current_password)
        except VerifyMismatchError:
            raise HTTPException(status_code=400, detail="Текущий пароль введен неверно")
        user.password_hash = ph.hash(user_data.new_password)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении в базу данных")
        
    return {"message": "ok"}

@app.post("/api/user/avatar")
async def update_avatar(file: UploadFile = File(...), request: Request = None, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)
    ext = file.filename.split('.')[-1]
    fname = f"avatar_{user.user_id}.{ext}"
    path = f"static/avatars/{fname}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    user.avatar_url = f"/static/avatars/{fname}"
    db.commit()
    return {"avatar_url": user.avatar_url}

from car_recommendation import get_car_recommendations
@app.get("/api/cars/recommended")
def get_recommended_cars(
    request: Request,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401)

    user = get_current_user(token, db)

    recommended_ids = get_car_recommendations(
        user_id=user.user_id,
        top_n=limit
    )

    if not recommended_ids:
        return []

    cars = (
        db.query(Car)
        .filter(Car.car_id.in_(recommended_ids))
        .filter(Car.seller_id != user.user_id) 
        .all()
    )

    cars_map = {c.car_id: c for c in cars}
    ordered_cars = [cars_map[i] for i in recommended_ids if i in cars_map]
    result = []
    for car in ordered_cars:
        result.append(format_car_dict(car, []))

    return result

@app.post("/api/cars")
def create_car(car_data: CarCreate, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)

    brand = db.query(Brand).filter(Brand.brand_name == car_data.brand).first()
    if not brand:
        db.add(Brand(brand_name=car_data.brand))
        db.commit()
    
    model = db.query(Model).filter(Model.model_name == car_data.model).first()
    if not model:
        db.add(Model(model_name=car_data.model, brand_name=car_data.brand))
        db.commit()

    body = db.query(BodyType).filter(BodyType.body_type_name == car_data.bodytype).first()
    if not body:
        db.add(BodyType(body_type_name=car_data.bodytype))
        db.commit()

    try:
        disp = float(str(car_data.engine_displacement).split('L')[0].strip())
    except:
        disp = 0.0

    car_dict = {
        "bodytype": car_data.bodytype,
        "brand": car_data.brand,
        "color": car_data.color,
        "fuel_type": car_data.fuel_type,
        "model": car_data.model,
        "vehicle_transmission": car_data.vehicle_transmission,
        "drive_type": car_data.drive_type,
        "wheel": car_data.wheel,
        "engine_displacement": disp,
        "engine_power": car_data.engine_power,
        "mileage": car_data.mileage,
        "production_date": car_data.production_date,
        "owners": car_data.owners
    }

    predicted_range = price_model.predict_price_range(car_dict)
    actual_range = price_model.price_to_range(car_data.price)
    price_range_diff = predicted_range - actual_range

    db_car = Car(
        seller_id=user.user_id,
        brand=car_data.brand,
        model=car_data.model,
        bodytype=car_data.bodytype,
        description=car_data.description,
        color=car_data.color,
        engine_displacement=disp,
        engine_power=car_data.engine_power,
        fuel_type=car_data.fuel_type,
        mileage=car_data.mileage,
        production_date=car_data.production_date,
        vehicle_transmission=car_data.vehicle_transmission,
        owners=car_data.owners,
        drive_type=car_data.drive_type,
        wheel=car_data.wheel,
        price=car_data.price,
        price_range=price_range_diff,         
        vin=car_data.vin,
        state_number=car_data.state_number
    )
    
    try:
        db.add(db_car)
        db.commit()
        db.refresh(db_car)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=str(e))
    
    return {"message": "Created", "car_id": db_car.car_id}

@app.get("/api/cars/{car_id}")
def get_car_details(car_id: int, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.car_id == car_id).first()
    if not car: 
        raise HTTPException(404, "Not found")
    
    photos = [{"photo_url": p.photo_url} for p in car.photos] if car.photos else []
    data = format_car_dict(car, photos)
    
    data['user_id'] = car.seller_id 

    if car.seller:
        sales_count = db.query(func.count(Car.car_id)).filter(
            Car.seller_id == car.seller.user_id
        ).scalar()
        
        data['seller'] = {
            "user_id": car.seller.user_id,
            "first_name": car.seller.first_name,
            "last_name": car.seller.last_name,
            "seller_phone": car.seller.phone,
            "sales_count": sales_count
        }
    else:
        data['seller'] = None
        
    return data

@app.get("/api/user/cars")
def get_user_cars(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)
    
    cars = db.query(Car).filter(Car.seller_id == user.user_id).all()
    res = []
    for c in cars:
        photos = [{"photo_url": p.photo_url} for p in c.photos] if c.photos else []
        res.append(format_car_dict(c, photos))
    return res

@app.get("/api/user/favorites")
def get_favorites(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)
    
    favs = db.query(Favorite).filter(Favorite.user_id == user.user_id).all()
    res = []
    for f in favs:
        if f.car_ref:
            photos = [{"photo_url": p.photo_url} for p in f.car_ref.photos] if f.car_ref.photos else []
            res.append(format_car_dict(f.car_ref, photos))
    return res

@app.post("/api/favorites/{car_id}")
def add_favorite(car_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)
    
    if db.query(Favorite).filter(Favorite.user_id == user.user_id, Favorite.car_id == car_id).first():
        return {"status": "exists"}
    
    db.add(Favorite(user_id=user.user_id, car_id=car_id))
    db.commit()
    return {"status": "added"}

@app.delete("/api/favorites/{car_id}")
def remove_favorite(car_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)
    db.query(Favorite).filter(Favorite.user_id == user.user_id, Favorite.car_id == car_id).delete()
    db.commit()
    return {"status": "removed"}

@app.delete("/api/cars/{car_id}")
def delete_car(car_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(401)
    user = get_current_user(token, db)
    car = db.query(Car).filter(Car.car_id == car_id, Car.seller_id == user.user_id).first()
    if not car: raise HTTPException(404)
    db.delete(car)
    db.commit()
    return {"message": "deleted"}

def format_car_dict(c, photos):
    return {
        "car_id": c.car_id,
        "brand": c.brand,
        "model": c.model,
        "price": float(c.price or 0),
        "mileage": c.mileage,
        "year": c.production_date,
        "production_date": c.production_date,
        "engine_displacement": float(c.engine_displacement or 0),
        "engine_power": float(c.engine_power or 0),
        "fuel_type": c.fuel_type,
        "vehicle_transmission": c.vehicle_transmission,
        "bodytype": c.bodytype,
        "body_type": c.bodytype, 
        "color": c.color,
        "drive_type": c.drive_type,
        "wheel": c.wheel,
        "owners": c.owners,
        "vin": c.vin,
        "state_number": c.state_number,
        "description": c.description,
        "price_range": c.price_range,
        "photos": photos
    }


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    if not request.cookies.get("access_token"):
        response = FileResponse("login.html")
    else:
        response = FileResponse("index.html")
    
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

@app.get("/login", response_class=HTMLResponse)
def read_login(request: Request):
    if request.cookies.get("access_token"):
        return FileResponse("index.html")
    return FileResponse("login.html")

@app.get("/{page_name}", response_class=HTMLResponse)
def serve_pages(page_name: str):
    if os.path.exists(page_name) and page_name.endswith(".html"):
        return FileResponse(page_name)
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, DECIMAL, create_engine
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker


engine = create_engine('sqlite:///cars_database.db', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    phone = Column(String, unique=True, nullable=False)
    avatar_url = Column(String)


    cars = relationship("Car", back_populates="seller")
    favorites = relationship("Favorite", back_populates="user")


class Brand(Base):
    __tablename__ = 'brands'

    brand_name = Column(String, primary_key=True)

    models = relationship("Model", back_populates="brand_ref")
    cars = relationship("Car", back_populates="brand_ref")


class Model(Base):
    __tablename__ = 'models'


    model_name = Column(String, primary_key=True)
    brand_name = Column(String, ForeignKey("brands.brand_name"))

    brand_ref = relationship("Brand", back_populates="models")
    cars = relationship("Car", back_populates="model_ref")


class BodyType(Base):
    __tablename__ = 'body_type'

    body_type_name = Column(String, primary_key=True)

    cars = relationship("Car", back_populates="body_type_ref")
    photos = relationship("Photo", back_populates="body_type_ref")


class Car(Base):
    __tablename__ = 'cars'

    car_id = Column(Integer, primary_key=True, autoincrement=True)
    

    seller_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    brand = Column(String, ForeignKey("brands.brand_name"), nullable=True) 
    model = Column(String, ForeignKey("models.model_name"), nullable=True)
    bodytype = Column(String, ForeignKey("body_type.body_type_name"), nullable=True) 

    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)
    engine_displacement = Column(DECIMAL, nullable=True) 
    engine_power = Column(DECIMAL, nullable=True)        
    fuel_type = Column(String, nullable=True)
    mileage = Column(Integer, nullable=True)
    production_date = Column(Integer, nullable=True)   
    vehicle_transmission = Column(String, nullable=True)
    owners = Column(Integer, nullable=True)
    drive_type = Column(String, nullable=True)        
    wheel = Column(String, nullable=True)               
    price = Column(DECIMAL, nullable=True)
    
    vin = Column(String, unique=True, nullable=True)
    state_number = Column(String, unique=True, nullable=True)
    price_range = Column(Integer, nullable=True) 

    
    seller = relationship("User", back_populates="cars")
    brand_ref = relationship("Brand", back_populates="cars")
    model_ref = relationship("Model", back_populates="cars")
    body_type_ref = relationship("BodyType", back_populates="cars")
    
    photos = relationship("Photo", back_populates="car_ref")
    favorites = relationship("Favorite", back_populates="car_ref")


class Photo(Base):
    __tablename__ = 'photos'

    photo_id = Column(Integer, primary_key=True, autoincrement=True)
    body_type = Column(String, ForeignKey("body_type.body_type_name"))
    car_id = Column(Integer, ForeignKey("cars.car_id"))
    photo_url = Column(String, nullable=False)

    body_type_ref = relationship("BodyType", back_populates="photos")
    car_ref = relationship("Car", back_populates="photos")


class Favorite(Base):
    __tablename__ = 'favorites'
    
    favorites_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    car_id = Column(Integer, ForeignKey("cars.car_id"))
    
    user = relationship("User", back_populates="favorites")
    car_ref = relationship("Car", back_populates="favorites")


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("ORM модели успешно инициализированы и соответствуют базе данных.")
    session.close()
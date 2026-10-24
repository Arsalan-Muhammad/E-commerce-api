from typing import Collection
from sqlalchemy.sql import text
from database import Base
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Boolean , Float
from sqlalchemy.orm import relationship

class products(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float , nullable=False)
    stock = Column(Integer , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)

class cart_items(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float , nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String , nullable=False , unique=True)
    password = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)    

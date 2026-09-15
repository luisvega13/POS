from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean,DateTime,ForeignKey,Integer,Numeric,String,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database import Base

MONEY=Numeric(12,2)
def now(): return datetime.now()

class Category(Base):
    __tablename__="categories"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(100),unique=True,index=True)
    active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)

class Product(Base):
    __tablename__="products"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(160),index=True)
    price: Mapped[Decimal]=mapped_column(MONEY)
    category: Mapped[str]=mapped_column(String(100),default="General",index=True)
    active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)

class CashSession(Base):
    __tablename__="cash_sessions"
    id: Mapped[int]=mapped_column(primary_key=True)
    opening_amount: Mapped[Decimal]=mapped_column(MONEY)
    opened_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)
    closed_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True,index=True)
    sales: Mapped[list["Sale"]]=relationship(back_populates="cash_session")

class Sale(Base):
    __tablename__="sales"
    id: Mapped[int]=mapped_column(primary_key=True)
    folio: Mapped[str]=mapped_column(String(12),unique=True,index=True)
    cash_session_id: Mapped[int]=mapped_column(ForeignKey("cash_sessions.id"),index=True)
    subtotal: Mapped[Decimal]=mapped_column(MONEY)
    total: Mapped[Decimal]=mapped_column(MONEY)
    payment_method: Mapped[str]=mapped_column(String(20),index=True)
    amount_received: Mapped[Decimal|None]=mapped_column(MONEY,nullable=True)
    change_amount: Mapped[Decimal|None]=mapped_column(MONEY,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)
    cash_session: Mapped[CashSession]=relationship(back_populates="sales")
    items: Mapped[list["SaleItem"]]=relationship(back_populates="sale",cascade="all, delete-orphan",order_by="SaleItem.id")

class SaleItem(Base):
    __tablename__="sale_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    sale_id: Mapped[int]=mapped_column(ForeignKey("sales.id"),index=True)
    product_id: Mapped[int|None]=mapped_column(ForeignKey("products.id"),nullable=True)
    product_name: Mapped[str]=mapped_column(String(160))
    unit_price: Mapped[Decimal]=mapped_column(MONEY)
    quantity: Mapped[int]=mapped_column(Integer)
    subtotal: Mapped[Decimal]=mapped_column(MONEY)
    sale: Mapped[Sale]=relationship(back_populates="items")

class BusinessConfig(Base):
    __tablename__="business_config"
    id: Mapped[int]=mapped_column(primary_key=True,default=1)
    business_name: Mapped[str]=mapped_column(String(160),default="MI NEGOCIO")
    address: Mapped[str]=mapped_column(String(240),default="")
    phone: Mapped[str]=mapped_column(String(60),default="")
    ticket_message: Mapped[str]=mapped_column(Text,default="¡Gracias por su compra!")
    printer_name: Mapped[str]=mapped_column(String(512),default="")
    encoding: Mapped[str]=mapped_column(String(40),default="cp850")
    character_table: Mapped[int|None]=mapped_column(Integer,nullable=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)

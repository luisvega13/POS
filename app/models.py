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
    declared_cash: Mapped[Decimal|None]=mapped_column(MONEY,nullable=True)
    declared_card: Mapped[Decimal|None]=mapped_column(MONEY,nullable=True)
    declared_transfer: Mapped[Decimal|None]=mapped_column(MONEY,nullable=True)
    reopened_count: Mapped[int]=mapped_column(Integer,default=0)
    last_reopened_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    last_reopened_by: Mapped[str]=mapped_column(String(120),default="")
    last_reopen_reason: Mapped[str]=mapped_column(String(240),default="")
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
    tip_amount: Mapped[Decimal]=mapped_column(MONEY,default=0)
    tip_method: Mapped[str|None]=mapped_column(String(20),nullable=True,index=True)
    discount_amount: Mapped[Decimal]=mapped_column(MONEY,default=0)
    discount_reason: Mapped[str]=mapped_column(String(240),default="")
    service_charge_percent: Mapped[int]=mapped_column(Integer,default=0)
    guest_count: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)
    cash_session: Mapped[CashSession]=relationship(back_populates="sales")
    items: Mapped[list["SaleItem"]]=relationship(back_populates="sale",cascade="all, delete-orphan",order_by="SaleItem.id")
    payments: Mapped[list["SalePayment"]]=relationship(back_populates="sale",cascade="all, delete-orphan",order_by="SalePayment.id")

class SalePayment(Base):
    __tablename__="sale_payments"
    id: Mapped[int]=mapped_column(primary_key=True)
    sale_id: Mapped[int]=mapped_column(ForeignKey("sales.id"),index=True)
    method: Mapped[str]=mapped_column(String(20),index=True)
    amount: Mapped[Decimal]=mapped_column(MONEY)
    sale: Mapped[Sale]=relationship(back_populates="payments")

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

class DiningTable(Base):
    __tablename__="dining_tables"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(80),index=True)
    status: Mapped[str]=mapped_column(String(20),default="open",index=True)
    opened_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)
    closed_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    account_printed_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True,index=True)
    guest_count: Mapped[int]=mapped_column(Integer,default=0)
    assigned_waiter_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    assigned_waiter_name: Mapped[str]=mapped_column(String(120),default="")
    cash_session_id: Mapped[int|None]=mapped_column(ForeignKey("cash_sessions.id"),nullable=True,index=True)
    items: Mapped[list["DiningTableItem"]]=relationship(back_populates="table",cascade="all, delete-orphan",order_by="DiningTableItem.id")

class DiningTableItem(Base):
    __tablename__="dining_table_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    table_id: Mapped[int]=mapped_column(ForeignKey("dining_tables.id"),index=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    product_name: Mapped[str]=mapped_column(String(160))
    unit_price: Mapped[Decimal]=mapped_column(MONEY)
    quantity: Mapped[int]=mapped_column(Integer)
    added_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)
    table: Mapped[DiningTable]=relationship(back_populates="items")

class TableItemCancellation(Base):
    __tablename__="table_item_cancellations"
    id: Mapped[int]=mapped_column(primary_key=True)
    table_id: Mapped[int]=mapped_column(ForeignKey("dining_tables.id"),index=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    product_name: Mapped[str]=mapped_column(String(160))
    unit_price: Mapped[Decimal]=mapped_column(MONEY)
    quantity: Mapped[int]=mapped_column(Integer)
    reason: Mapped[str]=mapped_column(String(240))
    cancelled_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    cancelled_by_name: Mapped[str]=mapped_column(String(120))
    cancelled_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)

class TableItemTransfer(Base):
    __tablename__="table_item_transfers"
    id: Mapped[int]=mapped_column(primary_key=True)
    source_table_id: Mapped[int]=mapped_column(ForeignKey("dining_tables.id"),index=True)
    target_table_id: Mapped[int]=mapped_column(ForeignKey("dining_tables.id"),index=True)
    product_name: Mapped[str]=mapped_column(String(160))
    quantity: Mapped[int]=mapped_column(Integer)
    transferred_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    transferred_by_name: Mapped[str]=mapped_column(String(120))
    transferred_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)

class CashCharge(Base):
    __tablename__="cash_charges"
    id: Mapped[int]=mapped_column(primary_key=True)
    cash_session_id: Mapped[int]=mapped_column(ForeignKey("cash_sessions.id"),index=True)
    amount: Mapped[Decimal]=mapped_column(MONEY)
    concept: Mapped[str]=mapped_column(String(240))
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    created_by_name: Mapped[str]=mapped_column(String(120))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    user_name: Mapped[str]=mapped_column(String(120),default="Sistema",index=True)
    user_role: Mapped[str]=mapped_column(String(20),default="system",index=True)
    action: Mapped[str]=mapped_column(String(80),index=True)
    entity_type: Mapped[str]=mapped_column(String(80),index=True)
    entity_id: Mapped[str]=mapped_column(String(80),default="",index=True)
    details: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now,index=True)

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

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    username: Mapped[str]=mapped_column(String(80),unique=True,index=True)
    display_name: Mapped[str]=mapped_column(String(120))
    password_hash: Mapped[str]=mapped_column(String(512))
    role: Mapped[str]=mapped_column(String(20),index=True)
    active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)
    sessions: Mapped[list["UserSession"]]=relationship(back_populates="user",cascade="all, delete-orphan")

class UserSession(Base):
    __tablename__="user_sessions"
    id: Mapped[int]=mapped_column(primary_key=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=now)
    user: Mapped[User]=relationship(back_populates="sessions")

class PermissionConfig(Base):
    __tablename__="permission_config"
    id: Mapped[int]=mapped_column(primary_key=True,default=1)
    cashier_table_access: Mapped[bool]=mapped_column(Boolean,default=True)
    waiter_print_account: Mapped[bool]=mapped_column(Boolean,default=True)
    waiter_transfer_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    cashier_transfer_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    waiter_product_transfer_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    cashier_product_transfer_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    waiter_table_transfer_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    cashier_table_transfer_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    waiter_cancel_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    cashier_cancel_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    cashier_discount_mode: Mapped[str]=mapped_column(String(20),default="allowed")
    waiter_reopen_printed_table: Mapped[bool]=mapped_column(Boolean,default=False)
    cashier_reopen_printed_table: Mapped[bool]=mapped_column(Boolean,default=True)
    waiter_reprint_account: Mapped[bool]=mapped_column(Boolean,default=True)
    cashier_reprint_account: Mapped[bool]=mapped_column(Boolean,default=True)
    cancel_password_hash: Mapped[str]=mapped_column(String(512),default="")
    transfer_password_hash: Mapped[str]=mapped_column(String(512),default="")
    product_transfer_password_hash: Mapped[str]=mapped_column(String(512),default="")
    table_transfer_password_hash: Mapped[str]=mapped_column(String(512),default="")
    discount_password_hash: Mapped[str]=mapped_column(String(512),default="")
    include_tip_in_ticket: Mapped[bool]=mapped_column(Boolean,default=True)
    service_charge_percent: Mapped[int]=mapped_column(Integer,default=10)
    include_suggested_tip: Mapped[bool]=mapped_column(Boolean,default=False)
    suggested_tip_percent: Mapped[int]=mapped_column(Integer,default=10)
    print_on_checkout: Mapped[bool]=mapped_column(Boolean,default=True)
    waiter_require_guest_count: Mapped[bool]=mapped_column(Boolean,default=False)
    developer_mode: Mapped[bool]=mapped_column(Boolean,default=False)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)

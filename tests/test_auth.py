from datetime import datetime
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.auth import authorize_operation,create_session,get_permissions,hash_password,require_roles,verify_password
from app.database import Base
from app.models import User,UserSession
from app.api.auth_routes import PermissionsPayload,update_permissions

@pytest.fixture
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool);Base.metadata.create_all(engine);session=sessionmaker(bind=engine,expire_on_commit=False)()
    yield session;session.close()

def test_password_hash_and_session_are_secure(db):
    encoded=hash_password("segura123");assert verify_password("segura123",encoded) and not verify_password("incorrecta",encoded)
    user=User(username="admin",display_name="Administrador",password_hash=encoded,role="admin");db.add(user);db.commit();db.refresh(user)
    raw=create_session(db,user);stored=db.scalar(select(UserSession).where(UserSession.user_id==user.id))
    assert raw!=stored.token_hash and len(stored.token_hash)==64 and stored.expires_at>datetime.now()

def test_role_permissions_reject_waiter_and_allow_admin():
    admin=User(username="admin",display_name="Admin",password_hash="x",role="admin",active=True)
    waiter=User(username="mesero",display_name="Mesero",password_hash="x",role="waiter",active=True)
    permission=require_roles("admin","cashier")
    assert permission(admin) is admin
    with pytest.raises(HTTPException) as denied:permission(waiter)
    assert denied.value.status_code==403
def test_each_operation_uses_its_own_password_or_can_be_blocked(db):
    admin=User(username="admin",display_name="Admin",password_hash=hash_password("admin123"),role="admin",active=True);waiter=User(username="mesero",display_name="Mesero",password_hash=hash_password("mesero123"),role="waiter",active=True);db.add_all([admin,waiter]);db.commit()
    policy=get_permissions(db);policy.waiter_product_transfer_mode="password";policy.waiter_table_transfer_mode="password";policy.waiter_cancel_mode="denied";policy.product_transfer_password_hash=hash_password("productos123");policy.table_transfer_password_hash=hash_password("mesa123");db.commit()
    with pytest.raises(HTTPException):authorize_operation(db,waiter,"product_transfer","incorrecta")
    authorize_operation(db,waiter,"product_transfer","productos123")
    authorize_operation(db,waiter,"table_transfer","mesa123")
    with pytest.raises(HTTPException):authorize_operation(db,waiter,"product_transfer","mesa123")
    with pytest.raises(HTTPException):authorize_operation(db,waiter,"table_transfer","admin123")
    with pytest.raises(HTTPException):authorize_operation(db,waiter,"cancel",None)

def test_permission_update_persists_discount_mode_and_operational_passwords(db):
    admin=User(username="admin",display_name="Admin",password_hash=hash_password("admin123"),role="admin",active=True);db.add(admin);db.commit();db.refresh(admin)
    payload=PermissionsPayload(cashier_table_access=True,waiter_print_account=True,waiter_product_transfer_mode="password",cashier_product_transfer_mode="allowed",waiter_table_transfer_mode="denied",cashier_table_transfer_mode="password",waiter_cancel_mode="allowed",cashier_cancel_mode="password",cashier_discount_mode="password",cancel_password="cancel123",product_transfer_password="productos123",table_transfer_password="mesas123",discount_password="descuento123",include_tip_in_ticket=False,service_charge_percent=10,include_suggested_tip=False,suggested_tip_percent=10,print_on_checkout=True,waiter_require_guest_count=False,developer_mode=False)
    saved=update_permissions(payload,admin,db);policy=get_permissions(db)
    assert saved["cashier_discount_mode"]=="password" and saved["discount_password_configured"] is True
    assert policy.cashier_discount_mode=="password" and verify_password("descuento123",policy.discount_password_hash)
    assert verify_password("productos123",policy.product_transfer_password_hash) and verify_password("mesas123",policy.table_transfer_password_hash) and verify_password("cancel123",policy.cancel_password_hash)

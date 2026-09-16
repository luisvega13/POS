from datetime import datetime
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.auth import authorize_operation,create_session,get_permissions,hash_password,require_roles,verify_password
from app.database import Base
from app.models import User,UserSession

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
def test_operation_can_require_admin_password_or_be_blocked(db):
    admin=User(username="admin",display_name="Admin",password_hash=hash_password("admin123"),role="admin",active=True);waiter=User(username="mesero",display_name="Mesero",password_hash=hash_password("mesero123"),role="waiter",active=True);db.add_all([admin,waiter]);db.commit()
    policy=get_permissions(db);policy.waiter_transfer_mode="password";policy.waiter_cancel_mode="denied";db.commit()
    with pytest.raises(HTTPException):authorize_operation(db,waiter,"transfer","incorrecta")
    authorize_operation(db,waiter,"transfer","admin123")
    with pytest.raises(HTTPException):authorize_operation(db,waiter,"cancel",None)

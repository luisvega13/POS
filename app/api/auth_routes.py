from datetime import datetime
from hashlib import sha256
from fastapi import APIRouter,Cookie,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.auth import COOKIE_NAME,ROLES,create_session,current_user_optional,get_permissions,hash_password,permissions_dict,require_roles,user_dict,verify_password
from app.database import get_db
from app.models import User,UserSession
from app.services.audit_service import record_audit

router=APIRouter(prefix="/api")
class Credentials(BaseModel):username:str=Field(min_length=3,max_length=80);password:str=Field(min_length=8,max_length=128)
class SetupPayload(Credentials):display_name:str=Field(min_length=2,max_length=120)
class UserPayload(SetupPayload):role:str
class UserUpdate(BaseModel):display_name:str|None=Field(default=None,min_length=2,max_length=120);role:str|None=None;active:bool|None=None;password:str|None=Field(default=None,min_length=8,max_length=128)
class PermissionsPayload(BaseModel):
    cashier_table_access:bool;waiter_print_account:bool;waiter_product_transfer_mode:str;cashier_product_transfer_mode:str;waiter_table_transfer_mode:str;cashier_table_transfer_mode:str;waiter_cancel_mode:str;cashier_cancel_mode:str;cashier_discount_mode:str;waiter_reopen_printed_table:bool=False;cashier_reopen_printed_table:bool=True;waiter_reprint_account:bool=True;cashier_reprint_account:bool=True;cancel_password:str|None=Field(default=None,min_length=4,max_length=128);product_transfer_password:str|None=Field(default=None,min_length=4,max_length=128);table_transfer_password:str|None=Field(default=None,min_length=4,max_length=128);discount_password:str|None=Field(default=None,min_length=4,max_length=128);include_tip_in_ticket:bool;service_charge_percent:int=Field(ge=0,le=100);include_suggested_tip:bool;suggested_tip_percent:int=Field(ge=0,le=100);print_on_checkout:bool;waiter_require_guest_count:bool;developer_mode:bool
def fail(message,status=400):raise HTTPException(status,detail={"success":False,"message":message})
def set_cookie(response:Response,token:str):response.set_cookie(COOKIE_NAME,token,max_age=43200,httponly=True,samesite="strict",secure=False,path="/")

@router.get("/auth/status")
def status(user:User|None=Depends(current_user_optional),db:Session=Depends(get_db)):
    return {"setup_required":db.scalar(select(func.count(User.id)))==0,"authenticated":bool(user),"user":user_dict(user) if user else None}
@router.post("/auth/setup",status_code=201)
def setup(payload:SetupPayload,response:Response,db:Session=Depends(get_db)):
    if db.scalar(select(func.count(User.id))):fail("La configuración inicial ya fue completada",409)
    user=User(username=payload.username.strip().lower(),display_name=payload.display_name.strip(),password_hash=hash_password(payload.password),role="admin");db.add(user);db.commit();db.refresh(user);set_cookie(response,create_session(db,user));return {"user":user_dict(user)}
@router.post("/auth/login")
def login(payload:Credentials,response:Response,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(func.lower(User.username)==payload.username.strip().lower()))
    if not user or not user.active or not verify_password(payload.password,user.password_hash):fail("Usuario o contraseña incorrectos",401)
    set_cookie(response,create_session(db,user));return {"user":user_dict(user)}
@router.post("/auth/logout")
def logout(response:Response,pos_session:str|None=Cookie(default=None),db:Session=Depends(get_db)):
    if pos_session:db.query(UserSession).filter(UserSession.token_hash==sha256(pos_session.encode()).hexdigest()).delete();db.commit()
    response.delete_cookie(COOKIE_NAME,path="/");return {"success":True}
@router.get("/users")
def users(_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):return [user_dict(user) for user in db.scalars(select(User).order_by(User.display_name))]
@router.get("/staff/waiters")
def waiters(_:User=Depends(require_roles("admin","cashier","waiter")),db:Session=Depends(get_db)):return [user_dict(user) for user in db.scalars(select(User).where(User.role=="waiter",User.active.is_(True)).order_by(User.display_name))]
@router.post("/users",status_code=201)
def create_user(payload:UserPayload,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    role=payload.role.lower()
    if role not in ROLES:fail("Perfil no válido")
    username=payload.username.strip().lower()
    if db.scalar(select(User).where(func.lower(User.username)==username)):fail("El nombre de usuario ya existe",409)
    user=User(username=username,display_name=payload.display_name.strip(),password_hash=hash_password(payload.password),role=role);db.add(user);db.commit();db.refresh(user);record_audit(db,_,"user.create","user",user.id,{"username":user.username,"role":user.role});return user_dict(user)
@router.put("/users/{user_id}")
def update_user(user_id:int,payload:UserUpdate,current:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    user=db.get(User,user_id)
    if not user:fail("Usuario no encontrado",404)
    values=payload.model_dump(exclude_unset=True)
    if values.get("role") and values["role"] not in ROLES:fail("Perfil no válido")
    if user.id==current.id and values.get("active") is False:fail("No puedes desactivar tu propia cuenta")
    password=values.pop("password",None)
    for key,value in values.items():setattr(user,key,value)
    if password:user.password_hash=hash_password(password)
    user.updated_at=datetime.now();db.commit();db.refresh(user);record_audit(db,current,"user.update","user",user.id,{"fields":list(values.keys()),"password_changed":bool(password)});return user_dict(user)
@router.get("/permissions")
def permissions(_:User=Depends(require_roles("admin","cashier","waiter")),db:Session=Depends(get_db)):return permissions_dict(get_permissions(db))
@router.put("/permissions")
def update_permissions(payload:PermissionsPayload,user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    values=payload.model_dump();passwords={key:values.pop(key) for key in ("cancel_password","product_transfer_password","table_transfer_password","discount_password")};modes={values[key] for key in ("waiter_product_transfer_mode","cashier_product_transfer_mode","waiter_table_transfer_mode","cashier_table_transfer_mode","waiter_cancel_mode","cashier_cancel_mode","cashier_discount_mode")}
    if not modes.issubset({"allowed","password","denied"}):fail("Modo de permiso no válido")
    if values["include_tip_in_ticket"] and values["include_suggested_tip"]:fail("Elige cargo de servicio o propina sugerida, no ambos")
    config=get_permissions(db)
    for key,value in values.items():setattr(config,key,value)
    for key,value in passwords.items():
        if value:setattr(config,f"{key}_hash",hash_password(value))
    config.updated_at=datetime.now();db.commit();db.refresh(config);record_audit(db,user,"permissions.update","permission_config",1,values);return permissions_dict(config)

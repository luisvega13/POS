from datetime import datetime,timedelta
from hashlib import pbkdf2_hmac,sha256
from hmac import compare_digest
from secrets import token_bytes,token_urlsafe
from fastapi import Cookie,Depends,HTTPException,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import PermissionConfig,User,UserSession

ROLES={"admin","cashier","waiter"}; COOKIE_NAME="pos_session"; SESSION_HOURS=12
def hash_password(password:str)->str:
    salt=token_bytes(16); digest=pbkdf2_hmac("sha256",password.encode(),salt,260000)
    return f"{salt.hex()}${digest.hex()}"
def verify_password(password:str,encoded:str)->bool:
    try:salt,digest=encoded.split("$",1); candidate=pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),260000).hex(); return compare_digest(candidate,digest)
    except (ValueError,TypeError):return False
def user_dict(user:User):return {"id":user.id,"username":user.username,"display_name":user.display_name,"role":user.role,"active":user.active,"created_at":user.created_at.isoformat()}
def create_session(db:Session,user:User):
    raw=token_urlsafe(32); db.add(UserSession(token_hash=sha256(raw.encode()).hexdigest(),user_id=user.id,expires_at=datetime.now()+timedelta(hours=SESSION_HOURS))); db.commit(); return raw
def current_user_optional(pos_session:str|None=Cookie(default=None),db:Session=Depends(get_db)):
    if not pos_session:return None
    digest=sha256(pos_session.encode()).hexdigest(); session=db.scalar(select(UserSession).where(UserSession.token_hash==digest,UserSession.expires_at>datetime.now()))
    if not session:return None
    user=db.get(User,session.user_id); return user if user and user.active else None
def get_permissions(db:Session):
    config=db.get(PermissionConfig,1)
    if not config:config=PermissionConfig(id=1);db.add(config);db.commit();db.refresh(config)
    return config
def permissions_dict(config:PermissionConfig):return {"cashier_table_access":config.cashier_table_access,"waiter_print_account":config.waiter_print_account,"waiter_transfer_mode":config.waiter_transfer_mode,"cashier_transfer_mode":config.cashier_transfer_mode,"waiter_cancel_mode":config.waiter_cancel_mode,"cashier_cancel_mode":config.cashier_cancel_mode,"include_tip_in_ticket":config.include_tip_in_ticket,"service_charge_percent":config.service_charge_percent,"include_suggested_tip":config.include_suggested_tip,"suggested_tip_percent":config.suggested_tip_percent,"print_on_checkout":config.print_on_checkout,"waiter_require_guest_count":config.waiter_require_guest_count,"developer_mode":config.developer_mode}
def require_user(request:Request,user:User|None=Depends(current_user_optional),db:Session=Depends(get_db)):
    if not user:raise HTTPException(401,detail={"success":False,"message":"Inicia sesión para continuar"})
    if user.role=="cashier" and request.url.path.startswith("/api/tables") and not get_permissions(db).cashier_table_access:raise HTTPException(403,detail={"success":False,"message":"El perfil Caja no tiene acceso a Mesas"})
    return user
def authorize_operation(db:Session,user:User,operation:str,password:str|None):
    if user.role=="admin":return
    config=get_permissions(db);mode=getattr(config,f"{user.role}_{operation}_mode", "denied")
    if mode=="denied":raise HTTPException(403,detail={"success":False,"message":"Tu perfil no tiene permiso para realizar esta operación"})
    if mode=="password":
        admins=db.scalars(select(User).where(User.role=="admin",User.active.is_(True))).all()
        if not password or not any(verify_password(password,admin.password_hash) for admin in admins):raise HTTPException(403,detail={"success":False,"message":"Contraseña de administrador incorrecta"})
def require_roles(*roles):
    def dependency(user:User=Depends(require_user)):
        if user.role not in roles:raise HTTPException(403,detail={"success":False,"message":"Tu perfil no tiene permiso para realizar esta acción"})
        return user
    return dependency

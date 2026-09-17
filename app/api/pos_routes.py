from datetime import date,datetime,time,timedelta
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from pydantic import BaseModel,Field
from sqlalchemy import distinct,select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import BusinessConfig,Product,User
from app.auth import authorize_operation,get_permissions,require_roles,require_user
from app.printer.printer_service import PrinterError
from app.services.pos_service import CashService,CategoryService,DiningTableService,PosError,ProductService,SaleService,config_dict,get_business_config,sale_dict
from app.services.audit_service import list_audits,record_audit
from app.services.print_service import deliver_ticket
from app.services.ticket_service import cash_ticket,sale_ticket,table_account_ticket

router=APIRouter(prefix="/api",dependencies=[Depends(require_user)])
class ProductCreate(BaseModel):
    name:str=Field(min_length=1,max_length=160); price:Decimal=Field(ge=0); category:str="General"; active:bool=True
class ProductUpdate(BaseModel):
    name:str|None=None; price:Decimal|None=Field(default=None,ge=0); category:str|None=None; active:bool|None=None
class SaleLine(BaseModel): product_id:int; quantity:int=Field(ge=1,le=999)
class PaymentLine(BaseModel):method:str;amount:Decimal=Field(gt=0)
class SaleCreate(BaseModel): items:list[SaleLine]; payment_method:str="cash";payments:list[PaymentLine]=Field(default_factory=list);amount_received:Decimal|None=None; tip_amount:Decimal=Field(default=0,ge=0); tip_method:str|None=None;discount_amount:Decimal=Field(default=0,ge=0);discount_reason:str="";discount_password:str|None=None; print_ticket:bool=True; guest_count:int=Field(default=0,ge=0)
class CashOpen(BaseModel): opening_amount:Decimal=Field(ge=0)
class CashClose(BaseModel):declared_cash:Decimal=Field(ge=0);declared_card:Decimal=Field(ge=0);declared_transfer:Decimal=Field(ge=0)
class CashChargePayload(BaseModel):amount:Decimal=Field(gt=0);concept:str=Field(min_length=2,max_length=240)
class CashReopenPayload(BaseModel):reason:str=Field(min_length=3,max_length=240)
class CategoryPayload(BaseModel): name:str=Field(min_length=1,max_length=100)
class TablePayload(BaseModel): name:str=Field(min_length=1,max_length=80);guest_count:int=Field(default=0,ge=0,le=100);waiter_id:int|None=None
class TableWaiterPayload(BaseModel): waiter_id:int;operation_password:str|None=None
class TableItemsPayload(BaseModel): items:list[SaleLine]
class TableCheckout(BaseModel): payment_method:str="cash";payments:list[PaymentLine]=Field(default_factory=list);amount_received:Decimal|None=None; tip_amount:Decimal=Field(default=0,ge=0); tip_method:str|None=None;discount_amount:Decimal=Field(default=0,ge=0);discount_reason:str="";discount_password:str|None=None; print_ticket:bool=True
class CancelTableItem(BaseModel):quantity:int=Field(ge=1);reason:str=Field(min_length=2,max_length=240);operation_password:str|None=None
class OperationAuthorization(BaseModel):operation:str;password:str|None=None
class TransferLine(BaseModel):item_id:int;quantity:int=Field(ge=1)
class TransferPayload(BaseModel):target_table_id:int;items:list[TransferLine];operation_password:str|None=None
class BusinessUpdate(BaseModel):
    business_name:str=Field(min_length=1,max_length=160); address:str=""; phone:str=""; ticket_message:str="¡Gracias por su compra!"; printer_name:str=""; encoding:str="cp850"; character_table:int|None=None
def fail(exc,status=400): raise HTTPException(status,detail={"success":False,"message":str(exc)}) from exc

@router.get("/products",tags=["products"])
def products(search:str="",category:str|None=None,include_inactive:bool=False,db:Session=Depends(get_db)):
    return ProductService.list(db,search,category,not include_inactive)
@router.get("/categories",tags=["categories"])
def categories(db:Session=Depends(get_db)): return CategoryService.list(db)
@router.post("/categories",status_code=201,tags=["categories"])
def create_category(payload:CategoryPayload,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:return CategoryService.create(db,payload.name)
    except PosError as exc:fail(exc)
@router.put("/categories/{category_id}",tags=["categories"])
def update_category(category_id:int,payload:CategoryPayload,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:return CategoryService.update(db,category_id,payload.name)
    except PosError as exc:fail(exc,404 if "encontrada" in str(exc) else 400)
@router.delete("/categories/{category_id}",tags=["categories"])
def delete_category(category_id:int,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:CategoryService.delete(db,category_id); return {"success":True,"message":"Categoría eliminada"}
    except PosError as exc:fail(exc,404 if "encontrada" in str(exc) else 409)
@router.get("/products/{product_id}",tags=["products"])
def product(product_id:int,db:Session=Depends(get_db)):
    item=db.get(Product,product_id)
    if not item: raise HTTPException(404,detail={"success":False,"message":"Producto no encontrado"})
    from app.services.pos_service import product_dict
    return product_dict(item)
@router.post("/products",status_code=201,tags=["products"])
def create_product(payload:ProductCreate,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:return ProductService.create(db,payload)
    except PosError as exc:fail(exc)
@router.put("/products/{product_id}",tags=["products"])
def update_product(product_id:int,payload:ProductUpdate,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:return ProductService.update(db,product_id,payload)
    except PosError as exc:fail(exc,404 if "encontrado" in str(exc) else 400)
@router.delete("/products/{product_id}",tags=["products"])
def delete_product(product_id:int,_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:
        class Patch:
            def model_dump(self,exclude_unset=True):return {"active":False}
        return ProductService.update(db,product_id,Patch())
    except PosError as exc:fail(exc,404)

@router.get("/sales",tags=["sales"])
def sales(limit:int=Query(200,ge=1,le=1000),_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)): return SaleService.list(db,limit)
@router.get("/sales-history",tags=["sales"])
def sales_history(page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100),day:date|None=None,_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    start=datetime.combine(day,time.min) if day else None;end=datetime.combine(day+timedelta(days=1),time.min) if day else None
    return SaleService.paginated(db,page,page_size,start,end)
@router.get("/reports/products-sold",tags=["reports"])
def products_sold(date_from:date|None=None,date_to:date|None=None,category:str|None=None,_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    start=datetime.combine(date_from,time.min) if date_from else None
    end=datetime.combine(date_to+timedelta(days=1),time.min) if date_to else None
    return SaleService.product_report(db,start,end,category)
@router.get("/sales/{sale_id}",tags=["sales"])
def sale(sale_id:int,_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:return sale_dict(SaleService.get(db,sale_id),True)
    except PosError as exc:fail(exc,404)
@router.post("/sales",status_code=201,tags=["sales"])
def create_sale(payload:SaleCreate,request:Request,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        if payload.discount_amount>0:authorize_operation(db,user,"discount",payload.discount_password)
        saved=SaleService.create(db,payload)
    except PosError as exc:fail(exc)
    record_audit(db,user,"sale.create","sale",saved.id,{"folio":saved.folio,"total":saved.total,"discount":saved.discount_amount,"discount_reason":saved.discount_reason});response={"success":True,"message":"Venta registrada correctamente","sale":sale_dict(saved,True),"print_success":None}
    if payload.print_ticket and get_permissions(db).print_on_checkout:
        try:
            config=get_business_config(db);response.update(deliver_ticket(request,db,sale_ticket(saved,config,get_permissions(db)),config.encoding,"Venta registrada y enviada al spooler de Windows"))
        except (PrinterError,LookupError,ValueError) as exc:
            response.update(print_success=False,print_error=str(exc),message="Venta registrada correctamente, pero ocurrió un error al imprimir")
    return response
@router.post("/sales/{sale_id}/print",tags=["sales"])
def reprint_sale(sale_id:int,request:Request,_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        saved=SaleService.get(db,sale_id);config=get_business_config(db)
        return deliver_ticket(request,db,sale_ticket(saved,config,get_permissions(db)),config.encoding,"Reimpresión enviada al spooler de Windows")
    except PosError as exc:fail(exc,404)
    except (PrinterError,LookupError,ValueError) as exc:fail(exc,503)

@router.get("/tables",tags=["tables"])
def tables(user:User=Depends(require_user),db:Session=Depends(get_db)): return DiningTableService.list(db,user)
@router.post("/operations/authorize",tags=["permissions"])
def authorize(payload:OperationAuthorization,user:User=Depends(require_user),db:Session=Depends(get_db)):
    if payload.operation not in {"cancel","product_transfer","table_transfer"}:fail(PosError("Operación no válida"))
    authorize_operation(db,user,payload.operation,payload.password);return {"success":True}
@router.post("/tables",status_code=201,tags=["tables"])
def create_table(payload:TablePayload,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:
        if user.role=="waiter" and get_permissions(db).waiter_require_guest_count and payload.guest_count<1: raise PosError("Indica cuántas personas ocuparán la mesa")
        if user.role!="waiter" and payload.waiter_id is None: raise PosError("Selecciona el mesero responsable de la mesa")
        return DiningTableService.create(db,payload.name,payload.guest_count,user,payload.waiter_id)
    except PosError as exc:fail(exc)
@router.put("/tables/{table_id}/waiter",tags=["tables"])
def assign_table_waiter(table_id:int,payload:TableWaiterPayload,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:
        DiningTableService.get(db,table_id,user);authorize_operation(db,user,"table_transfer",payload.operation_password)
        return DiningTableService.assign_waiter(db,table_id,payload.waiter_id)
    except PosError as exc:fail(exc,404 if "encontr" in str(exc) else 400)
@router.put("/tables/{table_id}/items",tags=["tables"])
def save_table_items(table_id:int,payload:TableItemsPayload,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:DiningTableService.get(db,table_id,user);return DiningTableService.save_items(db,table_id,payload.items)
    except PosError as exc:fail(exc,404 if "encontrada" in str(exc) else 400)
@router.post("/tables/{table_id}/items",tags=["tables"])
def add_table_items(table_id:int,payload:TableItemsPayload,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:DiningTableService.get(db,table_id,user);return DiningTableService.add_items(db,table_id,payload.items)
    except PosError as exc:fail(exc,404 if "encontrada" in str(exc) else 400)
@router.delete("/tables/{table_id}",tags=["tables"])
def cancel_table(table_id:int,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:DiningTableService.cancel(db,table_id);record_audit(db,user,"table.cancel","dining_table",table_id);return {"success":True,"message":"Mesa cerrada sin cobrar"}
    except PosError as exc:fail(exc,404)
@router.post("/tables/{table_id}/print-account",tags=["tables"])
def print_table_account(table_id:int,request:Request,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:
        permissions=get_permissions(db)
        if user.role=="waiter" and not permissions.waiter_print_account:fail(PosError("El perfil Mesero no tiene permiso para imprimir cuentas"),403)
        table=DiningTableService.get(db,table_id,user)
        if table.account_printed_at and user.role!="admin" and not (permissions.waiter_reprint_account if user.role=="waiter" else permissions.cashier_reprint_account):fail(PosError("Tu perfil no puede reimprimir cuentas"),403)
        if not table.items:raise PosError("La mesa no tiene productos")
        config=get_business_config(db)
        response=deliver_ticket(request,db,table_account_ticket(table,config,permissions),config.encoding,"Cuenta enviada a impresión sin cerrar la mesa")
        table.account_printed_at=datetime.now();table.updated_at=datetime.now();db.commit();record_audit(db,user,"table.account_printed","dining_table",table_id);return response
    except PosError as exc:fail(exc,404)
    except (PrinterError,LookupError,ValueError) as exc:fail(exc,503)
@router.post("/tables/{table_id}/reopen-account",tags=["tables"])
def reopen_table_account(table_id:int,user:User=Depends(require_user),db:Session=Depends(get_db)):
    permissions=get_permissions(db);allowed=permissions.waiter_reopen_printed_table if user.role=="waiter" else permissions.cashier_reopen_printed_table if user.role=="cashier" else True
    if not allowed:fail(PosError("Tu perfil no puede reabrir mesas con cuenta impresa"),403)
    try:result=DiningTableService.reopen_printed(db,table_id);record_audit(db,user,"table.account_reopened","dining_table",table_id);return result
    except PosError as exc:fail(exc)
@router.get("/tables/{table_id}/cancellations",tags=["tables"])
def table_cancellations(table_id:int,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:DiningTableService.get(db,table_id,user);return DiningTableService.cancellations(db,table_id)
    except PosError as exc:fail(exc,404)
@router.post("/tables/{table_id}/items/{item_id}/cancel",tags=["tables"])
def cancel_table_item(table_id:int,item_id:int,payload:CancelTableItem,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:
        DiningTableService.get(db,table_id,user);authorize_operation(db,user,"cancel",payload.operation_password);result=DiningTableService.cancel_item(db,table_id,item_id,payload.quantity,payload.reason,user);record_audit(db,user,"table.item_cancel","dining_table",table_id,{"item_id":item_id,"quantity":payload.quantity,"reason":payload.reason});return result
    except PosError as exc:fail(exc)
@router.post("/tables/{table_id}/transfer",tags=["tables"])
def transfer_table_items(table_id:int,payload:TransferPayload,user:User=Depends(require_user),db:Session=Depends(get_db)):
    try:
        DiningTableService.get(db,table_id,user);DiningTableService.get(db,payload.target_table_id,user);authorize_operation(db,user,"product_transfer",payload.operation_password);result=DiningTableService.transfer_items(db,table_id,payload.target_table_id,payload.items,user);record_audit(db,user,"table.product_transfer","dining_table",table_id,{"target_table_id":payload.target_table_id,"items":[item.model_dump() for item in payload.items]});return result
    except PosError as exc:fail(exc)
@router.post("/tables/{table_id}/checkout",tags=["tables"])
def checkout_table(table_id:int,payload:TableCheckout,request:Request,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        table=DiningTableService.ensure_editable(DiningTableService.get(db,table_id))
        if payload.discount_amount>0:authorize_operation(db,user,"discount",payload.discount_password)
        sale_payload=SaleCreate(items=[SaleLine(product_id=item.product_id,quantity=item.quantity) for item in table.items],payment_method=payload.payment_method,payments=payload.payments,amount_received=payload.amount_received,tip_amount=payload.tip_amount,tip_method=payload.tip_method,discount_amount=payload.discount_amount,discount_reason=payload.discount_reason,print_ticket=payload.print_ticket,guest_count=table.guest_count or 0)
        saved=SaleService.create(db,sale_payload); table=DiningTableService.get(db,table_id); table.status="closed"; table.closed_at=datetime.now(); table.updated_at=datetime.now(); db.commit()
    except PosError as exc:fail(exc)
    record_audit(db,user,"table.checkout","dining_table",table_id,{"sale_id":saved.id,"folio":saved.folio,"total":saved.total,"discount":saved.discount_amount});response={"success":True,"message":"Mesa cobrada y registrada correctamente","sale":sale_dict(saved,True),"print_success":None}
    if payload.print_ticket and get_permissions(db).print_on_checkout:
        try:
            config=get_business_config(db);response.update(deliver_ticket(request,db,sale_ticket(saved,config,get_permissions(db)),config.encoding,"Mesa cobrada y ticket enviado al spooler de Windows"))
        except (PrinterError,LookupError,ValueError) as exc:
            response.update(print_success=False,print_error=str(exc),message="Mesa cobrada, pero ocurrió un error al imprimir")
    return response

@router.get("/cash/current",tags=["cash"])
def current_cash(db:Session=Depends(get_db)):
    current=CashService.current(db)
    return {"open":bool(current),"session":CashService.summary(db,current) if current else None}
@router.post("/cash/open",status_code=201,tags=["cash"])
def open_cash(payload:CashOpen,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        summary=CashService.summary(db,CashService.open(db,payload.opening_amount));record_audit(db,user,"cash.open","cash_session",summary["id"],{"opening_amount":summary["opening_amount"]});return {"success":True,"session":summary}
    except PosError as exc:fail(exc)
@router.get("/cash/summary",tags=["cash"])
def cash_summary(_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:return CashService.summary(db)
    except PosError as exc:fail(exc,404)
@router.post("/cash/charges",tags=["cash"])
def add_cash_charge(payload:CashChargePayload,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        charge=CashService.add_charge(db,payload.amount,payload.concept,user);record_audit(db,user,"cash.charge","cash_charge",charge["id"],{"amount":charge["amount"],"concept":charge["concept"]});return {"success":True,"message":"Cargo registrado correctamente","charge":charge,"summary":CashService.summary(db)}
    except PosError as exc:fail(exc)
@router.post("/cash/close",tags=["cash"])
def close_cash(payload:CashClose,request:Request,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:summary=CashService.close(db,payload.declared_cash,payload.declared_card,payload.declared_transfer)
    except PosError as exc:fail(exc)
    record_audit(db,user,"cash.close","cash_session",summary["id"],{"declared_cash":summary["declared_cash"],"cash_variance":summary["cash_variance"]})
    response={"success":True,"message":"Caja cerrada correctamente","summary":summary,"print_success":None}
    try:
        config=get_business_config(db);response.update(deliver_ticket(request,db,cash_ticket(summary,config),config.encoding,"Caja cerrada y corte enviado al spooler de Windows"))
    except (PrinterError,LookupError,ValueError) as exc:
        response.update(print_success=False,print_error=str(exc),message="Caja cerrada, pero ocurrió un error al imprimir el corte")
    return response
@router.get("/cash/history",tags=["cash"])
def cash_history(page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=50),_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):return CashService.history(db,page,page_size)
@router.get("/cash/history/{session_id}",tags=["cash"])
def cash_history_detail(session_id:int,_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:return CashService.summary(db,CashService.get(db,session_id))
    except PosError as exc:fail(exc,404)
@router.post("/cash/history/{session_id}/reopen",tags=["cash"])
def reopen_cash(session_id:int,payload:CashReopenPayload,user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    try:
        summary=CashService.reopen(db,session_id,user,payload.reason);record_audit(db,user,"cash.reopen","cash_session",session_id,{"reason":payload.reason});return {"success":True,"message":"Corte reabierto correctamente","session":summary}
    except PosError as exc:fail(exc)
@router.post("/cash/history/{session_id}/print",tags=["cash"])
def print_historical_cash(session_id:int,request:Request,user:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        summary=CashService.summary(db,CashService.get(db,session_id));config=get_business_config(db);response=deliver_ticket(request,db,cash_ticket(summary,config),config.encoding,"Corte histórico enviado al spooler de Windows");record_audit(db,user,"cash.print_history","cash_session",session_id);return response
    except PosError as exc:fail(exc,404)
    except (PrinterError,LookupError,ValueError) as exc:fail(exc,503)
@router.post("/cash/print",tags=["cash"])
def print_cash(request:Request,_:User=Depends(require_roles("admin","cashier")),db:Session=Depends(get_db)):
    try:
        summary=CashService.summary(db);config=get_business_config(db)
        return deliver_ticket(request,db,cash_ticket(summary,config),config.encoding,"Corte enviado al spooler de Windows")
    except PosError as exc:fail(exc,404)
    except (PrinterError,LookupError,ValueError) as exc:fail(exc,503)

@router.get("/audit",tags=["audit"])
def audit_log(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),day:date|None=None,action:str="",_:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):return list_audits(db,page,page_size,day,action)

@router.get("/config",tags=["config"])
def business_config(db:Session=Depends(get_db)): return config_dict(get_business_config(db))
@router.put("/config",tags=["config"])
def update_config(payload:BusinessUpdate,request:Request,user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    if payload.character_table is not None and payload.character_table not in {*range(6),*range(16,20),255}: fail(PosError("Tabla de caracteres no documentada"))
    try: "test".encode(payload.encoding)
    except LookupError as exc: fail(PosError("Encoding de Python no válido"))
    c=get_business_config(db)
    values=payload.model_dump() if hasattr(payload,"model_dump") else payload.dict()
    for key,value in values.items(): setattr(c,key,value)
    db.commit(); db.refresh(c)
    legacy=request.app.state.config.load(); legacy.update({"printer_name":c.printer_name,"encoding":c.encoding,"character_table":c.character_table}); request.app.state.config.save(legacy);record_audit(db,user,"config.update","business_config",1,{"fields":list(values.keys())})
    return {"success":True,"message":"Configuración guardada","config":config_dict(c)}

from datetime import date,datetime,time,timedelta
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from pydantic import BaseModel,Field
from sqlalchemy import distinct,select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import BusinessConfig,Product
from app.printer.printer_service import PrinterError
from app.services.pos_service import CashService,CategoryService,PosError,ProductService,SaleService,config_dict,get_business_config,sale_dict
from app.services.ticket_service import cash_ticket,sale_ticket

router=APIRouter(prefix="/api")
class ProductCreate(BaseModel):
    name:str=Field(min_length=1,max_length=160); price:Decimal=Field(ge=0); category:str="General"; active:bool=True
class ProductUpdate(BaseModel):
    name:str|None=None; price:Decimal|None=Field(default=None,ge=0); category:str|None=None; active:bool|None=None
class SaleLine(BaseModel): product_id:int; quantity:int=Field(ge=1,le=999)
class SaleCreate(BaseModel): items:list[SaleLine]; payment_method:str; amount_received:Decimal|None=None; print_ticket:bool=True
class CashOpen(BaseModel): opening_amount:Decimal=Field(ge=0)
class CategoryPayload(BaseModel): name:str=Field(min_length=1,max_length=100)
class BusinessUpdate(BaseModel):
    business_name:str=Field(min_length=1,max_length=160); address:str=""; phone:str=""; ticket_message:str="¡Gracias por su compra!"; printer_name:str=""; encoding:str="cp850"; character_table:int|None=None
def fail(exc,status=400): raise HTTPException(status,detail={"success":False,"message":str(exc)}) from exc

@router.get("/products",tags=["products"])
def products(search:str="",category:str|None=None,include_inactive:bool=False,db:Session=Depends(get_db)):
    return ProductService.list(db,search,category,not include_inactive)
@router.get("/categories",tags=["categories"])
def categories(db:Session=Depends(get_db)): return CategoryService.list(db)
@router.post("/categories",status_code=201,tags=["categories"])
def create_category(payload:CategoryPayload,db:Session=Depends(get_db)):
    try:return CategoryService.create(db,payload.name)
    except PosError as exc:fail(exc)
@router.put("/categories/{category_id}",tags=["categories"])
def update_category(category_id:int,payload:CategoryPayload,db:Session=Depends(get_db)):
    try:return CategoryService.update(db,category_id,payload.name)
    except PosError as exc:fail(exc,404 if "encontrada" in str(exc) else 400)
@router.delete("/categories/{category_id}",tags=["categories"])
def delete_category(category_id:int,db:Session=Depends(get_db)):
    try:CategoryService.delete(db,category_id); return {"success":True,"message":"Categoría eliminada"}
    except PosError as exc:fail(exc,404 if "encontrada" in str(exc) else 409)
@router.get("/products/{product_id}",tags=["products"])
def product(product_id:int,db:Session=Depends(get_db)):
    item=db.get(Product,product_id)
    if not item: raise HTTPException(404,detail={"success":False,"message":"Producto no encontrado"})
    from app.services.pos_service import product_dict
    return product_dict(item)
@router.post("/products",status_code=201,tags=["products"])
def create_product(payload:ProductCreate,db:Session=Depends(get_db)):
    try:return ProductService.create(db,payload)
    except PosError as exc:fail(exc)
@router.put("/products/{product_id}",tags=["products"])
def update_product(product_id:int,payload:ProductUpdate,db:Session=Depends(get_db)):
    try:return ProductService.update(db,product_id,payload)
    except PosError as exc:fail(exc,404 if "encontrado" in str(exc) else 400)
@router.delete("/products/{product_id}",tags=["products"])
def delete_product(product_id:int,db:Session=Depends(get_db)):
    try:
        class Patch:
            def model_dump(self,exclude_unset=True):return {"active":False}
        return ProductService.update(db,product_id,Patch())
    except PosError as exc:fail(exc,404)

@router.get("/sales",tags=["sales"])
def sales(limit:int=Query(200,ge=1,le=1000),db:Session=Depends(get_db)): return SaleService.list(db,limit)
@router.get("/reports/products-sold",tags=["reports"])
def products_sold(date_from:date|None=None,date_to:date|None=None,db:Session=Depends(get_db)):
    start=datetime.combine(date_from,time.min) if date_from else None
    end=datetime.combine(date_to+timedelta(days=1),time.min) if date_to else None
    return SaleService.product_report(db,start,end)
@router.get("/sales/{sale_id}",tags=["sales"])
def sale(sale_id:int,db:Session=Depends(get_db)):
    try:return sale_dict(SaleService.get(db,sale_id),True)
    except PosError as exc:fail(exc,404)
@router.post("/sales",status_code=201,tags=["sales"])
def create_sale(payload:SaleCreate,request:Request,db:Session=Depends(get_db)):
    try:saved=SaleService.create(db,payload)
    except PosError as exc:fail(exc)
    response={"success":True,"message":"Venta registrada correctamente","sale":sale_dict(saved,True),"print_success":None}
    if payload.print_ticket:
        try:
            sent=request.app.state.printer.print_ticket(sale_ticket(saved,get_business_config(db)))
            response.update(print_success=True,bytes_sent=sent,message="Venta registrada y enviada al spooler de Windows")
        except (PrinterError,LookupError,ValueError) as exc:
            response.update(print_success=False,print_error=str(exc),message="Venta registrada correctamente, pero ocurrió un error al imprimir")
    return response
@router.post("/sales/{sale_id}/print",tags=["sales"])
def reprint_sale(sale_id:int,request:Request,db:Session=Depends(get_db)):
    try:
        saved=SaleService.get(db,sale_id); sent=request.app.state.printer.print_ticket(sale_ticket(saved,get_business_config(db)))
        return {"success":True,"message":"Reimpresión enviada al spooler de Windows","bytes_sent":sent}
    except PosError as exc:fail(exc,404)
    except (PrinterError,LookupError,ValueError) as exc:fail(exc,503)

@router.get("/cash/current",tags=["cash"])
def current_cash(db:Session=Depends(get_db)):
    current=CashService.current(db)
    return {"open":bool(current),"session":CashService.summary(db,current) if current else None}
@router.post("/cash/open",status_code=201,tags=["cash"])
def open_cash(payload:CashOpen,db:Session=Depends(get_db)):
    try:return {"success":True,"session":CashService.summary(db,CashService.open(db,payload.opening_amount))}
    except PosError as exc:fail(exc)
@router.get("/cash/summary",tags=["cash"])
def cash_summary(db:Session=Depends(get_db)):
    try:return CashService.summary(db)
    except PosError as exc:fail(exc,404)
@router.post("/cash/close",tags=["cash"])
def close_cash(db:Session=Depends(get_db)):
    try:return {"success":True,"message":"Caja cerrada correctamente","summary":CashService.close(db)}
    except PosError as exc:fail(exc)
@router.post("/cash/print",tags=["cash"])
def print_cash(request:Request,db:Session=Depends(get_db)):
    try:
        summary=CashService.summary(db); sent=request.app.state.printer.print_ticket(cash_ticket(summary,get_business_config(db)))
        return {"success":True,"message":"Corte enviado al spooler de Windows","bytes_sent":sent}
    except PosError as exc:fail(exc,404)
    except (PrinterError,LookupError,ValueError) as exc:fail(exc,503)

@router.get("/config",tags=["config"])
def business_config(db:Session=Depends(get_db)): return config_dict(get_business_config(db))
@router.put("/config",tags=["config"])
def update_config(payload:BusinessUpdate,request:Request,db:Session=Depends(get_db)):
    if payload.character_table is not None and payload.character_table not in {*range(6),*range(16,20),255}: fail(PosError("Tabla de caracteres no documentada"))
    try: "test".encode(payload.encoding)
    except LookupError as exc: fail(PosError("Encoding de Python no válido"))
    c=get_business_config(db)
    values=payload.model_dump() if hasattr(payload,"model_dump") else payload.dict()
    for key,value in values.items(): setattr(c,key,value)
    db.commit(); db.refresh(c)
    legacy=request.app.state.config.load(); legacy.update({"printer_name":c.printer_name,"encoding":c.encoding,"character_table":c.character_table}); request.app.state.config.save(legacy)
    return {"success":True,"message":"Configuración guardada","config":config_dict(c)}

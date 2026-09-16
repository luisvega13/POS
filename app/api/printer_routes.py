from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import require_roles
from app.database import get_db
from pydantic import BaseModel, Field
from app.printer.printer_service import PrinterError
from app.printer.ticket_builder import TicketBuilder
from app.services.print_service import deliver_ticket
from sqlalchemy.orm import Session

router=APIRouter(prefix="/api",tags=["printer"],dependencies=[Depends(require_roles("admin"))])
class PrinterSelection(BaseModel): printer_name: str=Field(min_length=1,max_length=512)
class CharacterTableSelection(BaseModel):
    character_table: int | None = None
class TextJob(BaseModel):
    text: str=Field(min_length=1,max_length=20000)
    align: str="left"
    bold: bool=False
    size: str="normal"

def svc(r): return r.app.state.printer,r.app.state.config
def output(n): return {"success":True,"message":"Trabajo enviado correctamente al spooler de Windows","bytes_sent":n}
def send(request,db,data,encoding):
    try: return deliver_ticket(request,db,data,encoding,"Trabajo enviado correctamente al spooler de Windows")
    except PrinterError as exc: raise HTTPException(503,detail={"success":False,"message":str(exc)}) from exc
def builder(config):
    values=config.load(); result=TicketBuilder(values["encoding"]).initialize()
    if values.get("character_table") is not None: result.character_table(values["character_table"])
    return result

@router.get("/printers")
def printers(request: Request):
    try: return svc(request)[0].get_printers()
    except PrinterError as exc: raise HTTPException(503,detail={"success":False,"message":str(exc)}) from exc
@router.get("/printer/config")
def config(request: Request): return svc(request)[1].load()
@router.post("/config/printer")
def select(payload: PrinterSelection,request: Request):
    printer,config=svc(request)
    try: printer.set_printer(payload.printer_name); return {"success":True,"message":"Impresora seleccionada","config":config.load()}
    except PrinterError as exc: raise HTTPException(400,detail={"success":False,"message":str(exc)}) from exc
@router.post("/config/character-table")
def select_character_table(payload: CharacterTableSelection,request: Request):
    config=svc(request)[1]
    if payload.character_table is not None and payload.character_table not in {*range(6),*range(16,20),255}:
        raise HTTPException(422,detail={"success":False,"message":"Tabla no documentada por el manual"})
    return {"success":True,"message":"Tabla de caracteres guardada","config":config.set_character_table(payload.character_table)}
@router.post("/print/text")
def text(payload: TextJob,request: Request,db:Session=Depends(get_db)):
    printer,config=svc(request)
    try: data=(builder(config).align(payload.align).bold(payload.bold).size(payload.size).text(payload.text).normal_size().bold(False).feed(4).build())
    except (ValueError,LookupError) as exc: raise HTTPException(422,detail={"success":False,"message":str(exc)}) from exc
    return send(request,db,data,config.load()["encoding"])
@router.post("/print/test")
def test(request: Request,db:Session=Depends(get_db)):
    printer,config=svc(request); b=builder(config)
    data=(b.align_center().bold(True).double_width().text("PRUEBA DE IMPRESION").normal_size().bold(False).align_left().line().text("Producto 1               $100.00").text("Producto 2                $50.00").line().bold(True).text("TOTAL                    $150.00").bold(False).text("").text("Prueba español:").text("á é í ó ú ü ñ Ñ ¿ ¡").text("").align_center().text("Impresion enviada").feed(4).build())
    return send(request,db,data,config.load()["encoding"])
@router.post("/print/characters")
def chars(request: Request,db:Session=Depends(get_db)):
    printer,config=svc(request); encoding=config.load()["encoding"]
    data=(builder(config).align_center().bold(True).text("PRUEBA DE CARACTERES").bold(False).align_left().text(f"Encoding: {encoding}").text("á é í ó ú ü ñ Ñ ¿ ¡").text("Á É Í Ó Ú Ü").text("$ # % & / ( ) = + -").feed(4).build())
    return send(request,db,data,encoding)
@router.post("/print/character-table-test")
def character_table_test(request: Request,db:Session=Depends(get_db)):
    printer,config=svc(request); encoding=config.load()["encoding"]
    b=TicketBuilder(encoding).initialize().align_center().bold(True).text("DIAGNOSTICO DE TABLAS").bold(False).align_left()
    for table in [0,1,2,3,4,5,16,17,18,19,255]:
        b.character_table(table).text(f"Tabla ESC t {table}: ñ Ñ á é í ó ú ü")
    return send(request,db,b.feed(4).build(),encoding)
@router.post("/print/format-test")
def formats(request: Request,db:Session=Depends(get_db)):
    printer,config=svc(request); b=builder(config)
    data=(b.align_center().bold(True).text("PRUEBA DE FORMATO").bold(False).align_left().text("Alineado a la izquierda").align_center().text("Centrado").align_right().text("Alineado a la derecha").align_left().normal_size().text("Tamaño normal").double_width().text("Doble ancho").double_height().text("Doble alto").double_size().text("Doble ancho y alto").normal_size().bold(True).text("Texto en negrita").bold(False).feed(4).build())
    return send(request,db,data,config.load()["encoding"])

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.pos_routes import router as pos_router
from app.api.printer_routes import router as printer_router
from app.database import SessionLocal,init_db
from app.services.pos_service import CategoryService,get_business_config
from app.printer.printer_service import ThermalPrinterService
from app.services.config_service import ConfigService

ROOT=Path(__file__).resolve().parent.parent; LOG_DIR=ROOT/"logs"; LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s: %(message)s",handlers=[logging.FileHandler(LOG_DIR/"app.log",encoding="utf-8"),logging.StreamHandler()])
@asynccontextmanager
async def lifespan(app):
    init_db()
    with SessionLocal() as db:
        CategoryService.ensure(db); business=get_business_config(db); legacy=app.state.config.load()
        if not business.printer_name and legacy.get("printer_name"):
            business.printer_name=legacy["printer_name"]; business.encoding=legacy.get("encoding","cp850"); business.character_table=legacy.get("character_table"); db.commit()
    logging.info("Sistema POS iniciado en 127.0.0.1:8000"); yield; logging.info("Servidor detenido")
app=FastAPI(title="POS térmico 58 mm",version="2.0.0",lifespan=lifespan)
app.state.config=ConfigService(ROOT/"config.json"); app.state.printer=ThermalPrinterService(app.state.config)
app.include_router(pos_router); app.include_router(printer_router); app.mount("/static",StaticFiles(directory=ROOT/"app"/"static"),name="static")
templates=Jinja2Templates(directory=ROOT/"app"/"templates")
@app.exception_handler(RequestValidationError)
async def invalid(_,exc): return JSONResponse(status_code=422,content={"success":False,"message":"Datos de solicitud no válidos"})
@app.exception_handler(Exception)
async def unexpected(_,exc): logging.exception("Error no controlado",exc_info=exc); return JSONResponse(status_code=500,content={"success":False,"message":"Error interno del servidor"})
@app.get("/",include_in_schema=False)
def home(request: Request): return templates.TemplateResponse(request=request,name="index.html")
if __name__=="__main__": uvicorn.run("app.main:app",host="127.0.0.1",port=8000)

from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import Product
from app.services.pos_service import CashService,CategoryService,PosError,ProductService,SaleService

@pytest.fixture
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine); session=sessionmaker(bind=engine,expire_on_commit=False)(); CategoryService.ensure(session); CategoryService.create(session,"Bebidas"); CategoryService.create(session,"Comida")
    yield session
    session.close()
def product_payload(name="Coca Cola",price="25.00",category="Bebidas",active=True): return SimpleNamespace(name=name,price=Decimal(price),category=category,active=active)
def sale_payload(items,method="cash",received="100.00"): return SimpleNamespace(items=[SimpleNamespace(product_id=i,quantity=q) for i,q in items],payment_method=method,amount_received=Decimal(received) if received is not None else None)
def test_create_and_edit_product(db):
    p=ProductService.create(db,product_payload()); assert p["price"]=="25.00"
    patch=SimpleNamespace(model_dump=lambda exclude_unset=True:{"name":"Coca Cola 600ml","price":Decimal("27.50")})
    updated=ProductService.update(db,p["id"],patch); assert updated["name"]=="Coca Cola 600ml" and updated["price"]=="27.50"
def test_sale_requires_open_cash(db):
    p=ProductService.create(db,product_payload())
    with pytest.raises(PosError): SaleService.create(db,sale_payload([(p["id"],1)]))
def test_cash_sale_multiple_products_and_change(db):
    a=ProductService.create(db,product_payload()); b=ProductService.create(db,product_payload("Papas","40","Comida")); CashService.open(db,"500")
    sale=SaleService.create(db,sale_payload([(a["id"],2),(b["id"],1)],"cash","100"))
    assert sale.folio=="000001" and sale.total==Decimal("90.00") and sale.change_amount==Decimal("10.00") and len(sale.items)==2
    summary=CashService.summary(db); assert summary["cash"]=="90.00" and summary["expected_cash"]=="590.00" and summary["operations"]==1
def test_card_transfer_and_consecutive_folios(db):
    p=ProductService.create(db,product_payload()); CashService.open(db,0)
    card=SaleService.create(db,sale_payload([(p["id"],1)],"card",None)); transfer=SaleService.create(db,sale_payload([(p["id"],2)],"transfer",None))
    assert (card.folio,transfer.folio)==("000001","000002")
    summary=CashService.summary(db); assert summary["card"]=="25.00" and summary["transfer"]=="50.00" and summary["total_sold"]=="75.00"
def test_historical_price_and_name_are_preserved(db):
    p=ProductService.create(db,product_payload()); CashService.open(db,0); sale=SaleService.create(db,sale_payload([(p["id"],1)],"card",None))
    model=db.get(Product,p["id"]); model.name="Nuevo nombre"; model.price=Decimal("99.00"); db.commit(); historical=SaleService.get(db,sale.id)
    assert historical.items[0].product_name=="Coca Cola" and historical.items[0].unit_price==Decimal("25.00")
def test_cash_rejects_insufficient_payment(db):
    p=ProductService.create(db,product_payload()); CashService.open(db,0)
    with pytest.raises(PosError): SaleService.create(db,sale_payload([(p["id"],1)],"cash","20"))
def test_category_create_rename_and_delete_rules(db):
    category=CategoryService.create(db,"Postres")
    product=ProductService.create(db,product_payload("Pastel","55","Postres"))
    renamed=CategoryService.update(db,category["id"],"Dulces")
    assert renamed["name"]=="Dulces" and db.get(Product,product["id"]).category=="Dulces"
    with pytest.raises(PosError): CategoryService.delete(db,category["id"])
def test_products_sold_report(db):
    a=ProductService.create(db,product_payload()); b=ProductService.create(db,product_payload("Papas","40","Comida")); CashService.open(db,0)
    SaleService.create(db,sale_payload([(a["id"],3),(b["id"],2)],"card",None)); SaleService.create(db,sale_payload([(a["id"],1)],"transfer",None))
    report=SaleService.product_report(db)
    assert report["total_units"]==6 and report["distinct_products"]==2 and report["total_revenue"]=="180.00"
    coca=next(x for x in report["products"] if x["product_name"]=="Coca Cola")
    assert coca["quantity"]==4 and coca["sales_count"]==2 and coca["revenue"]=="100.00"

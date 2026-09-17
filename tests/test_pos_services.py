from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import PermissionConfig,Product,User
from app.services.pos_service import CashService,CategoryService,DiningTableService,PosError,ProductService,SaleService
from app.services.audit_service import list_audits,record_audit

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
    summary=CashService.summary(db); assert summary["cash"]=="90.00" and summary["total_collected"]=="590.00" and summary["expected_cash"]=="590.00" and summary["operations"]==1
def test_card_transfer_and_consecutive_folios(db):
    p=ProductService.create(db,product_payload()); CashService.open(db,0)
    card=SaleService.create(db,sale_payload([(p["id"],1)],"card",None)); transfer=SaleService.create(db,sale_payload([(p["id"],2)],"transfer",None))
    assert (card.folio,transfer.folio)==("000001","000002")
    summary=CashService.summary(db); assert summary["card"]=="25.00" and summary["transfer"]=="50.00" and summary["total_sold"]=="75.00"
def test_split_payment_is_persisted_and_separated_in_cash_summary(db):
    product=ProductService.create(db,product_payload(price="100"));CashService.open(db,"20")
    payload=sale_payload([(product["id"],1)],"cash","50");payload.payments=[SimpleNamespace(method="cash",amount=Decimal("50")),SimpleNamespace(method="card",amount=Decimal("20")),SimpleNamespace(method="transfer",amount=Decimal("30"))]
    sale=SaleService.create(db,payload);detail=SaleService.get(db,sale.id);summary=CashService.summary(db)
    assert sale.payment_method=="mixed" and [(row.method,row.amount) for row in detail.payments]==[("cash",Decimal("50.00")),("card",Decimal("20.00")),("transfer",Decimal("30.00"))]
    assert summary["cash"]=="50.00" and summary["card"]=="20.00" and summary["transfer"]=="30.00" and summary["total_sold"]=="100.00"
def test_split_payment_must_equal_discounted_total(db):
    product=ProductService.create(db,product_payload(price="100"));CashService.open(db,0)
    payload=sale_payload([(product["id"],1)],"cash","40");payload.payments=[SimpleNamespace(method="cash",amount=Decimal("40")),SimpleNamespace(method="card",amount=Decimal("40"))]
    with pytest.raises(PosError,match="suma de los pagos"):SaleService.create(db,payload)
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
    assert coca["category"]=="Bebidas"
    filtered=SaleService.product_report(db,category="Comida")
    assert [row["product_name"] for row in filtered["products"]]==["Papas"]
def test_sales_history_is_paginated_in_groups_of_ten(db):
    product=ProductService.create(db,product_payload());CashService.open(db,0)
    for _ in range(12):SaleService.create(db,sale_payload([(product["id"],1)],"card",None))
    first=SaleService.paginated(db,1,10);second=SaleService.paginated(db,2,10)
    assert first["total"]==12 and len(first["items"])==10 and len(second["items"])==2
    assert first["items"][0]["folio"]=="000012" and second["items"][-1]["folio"]=="000001"
def test_multiple_tables_keep_independent_persistent_orders(db):
    drink=ProductService.create(db,product_payload()); food=ProductService.create(db,product_payload("Papas","40","Comida"))
    first=DiningTableService.create(db,"Mesa 1"); second=DiningTableService.create(db,"Terraza 2")
    DiningTableService.save_items(db,first["id"],[SimpleNamespace(product_id=drink["id"],quantity=2)])
    DiningTableService.save_items(db,second["id"],[SimpleNamespace(product_id=food["id"],quantity=1)])
    opened=DiningTableService.list(db)
    assert len(opened)==2 and opened[0]["total"]=="50.00" and opened[1]["total"]=="40.00"
    DiningTableService.cancel(db,first["id"])
    assert [table["name"] for table in DiningTableService.list(db)]==["Terraza 2"]
def test_waiter_only_lists_and_accesses_assigned_tables(db):
    first=User(username="mesero1",display_name="Mesero Uno",password_hash="x",role="waiter");second=User(username="mesero2",display_name="Mesero Dos",password_hash="x",role="waiter");db.add_all([first,second]);db.commit();db.refresh(first);db.refresh(second)
    own=DiningTableService.create(db,"Mesa propia",0,first);DiningTableService.create(db,"Mesa ajena",0,second)
    assert [table["name"] for table in DiningTableService.list(db,first)]==["Mesa propia"]
    assert DiningTableService.get(db,own["id"],first).assigned_waiter_id==first.id
    with pytest.raises(PosError,match="No tienes acceso"):DiningTableService.get(db,DiningTableService.list(db,second)[0]["id"],first)
def test_table_additions_preserve_separate_timestamps(db):
    product=ProductService.create(db,product_payload()); table=DiningTableService.create(db,"Mesa 3")
    first=DiningTableService.add_items(db,table["id"],[SimpleNamespace(product_id=product["id"],quantity=1)])
    second=DiningTableService.add_items(db,table["id"],[SimpleNamespace(product_id=product["id"],quantity=2)])
    assert len(first["items"])==1 and len(second["items"])==2
    assert all(item["added_at"] for item in second["items"]) and second["total"]=="75.00"
def test_printed_table_is_locked_until_reopened(db):
    product=ProductService.create(db,product_payload());table=DiningTableService.create(db,"Mesa bloqueada");DiningTableService.add_items(db,table["id"],[SimpleNamespace(product_id=product["id"],quantity=1)])
    model=DiningTableService.get(db,table["id"]);model.account_printed_at=datetime.now();db.commit()
    with pytest.raises(PosError,match="cuenta ya fue impresa"):DiningTableService.add_items(db,table["id"],[SimpleNamespace(product_id=product["id"],quantity=1)])
    reopened=DiningTableService.reopen_printed(db,table["id"]);assert reopened["account_printed_at"] is None
    saved=DiningTableService.add_items(db,table["id"],[SimpleNamespace(product_id=product["id"],quantity=1)]);assert len(saved["items"])==2
def test_tip_is_separated_by_method_in_cash_summary(db):
    product=ProductService.create(db,product_payload());CashService.open(db,0)
    payload=sale_payload([(product["id"],1)],"card","15");payload.tip_amount=Decimal("15");payload.tip_method="cash"
    SaleService.create(db,payload);summary=CashService.summary(db)
    assert summary["card"]=="25.00" and summary["tip_cash"]=="15.00" and summary["expected_cash"]=="0.00" and summary["grand_total"]=="40.00"
def test_card_and_transfer_tips_are_paid_from_expected_cash(db):
    product=ProductService.create(db,product_payload());CashService.open(db,"100")
    card=sale_payload([(product["id"],1)],"card",None);card.tip_amount=Decimal("5");card.tip_method="card"
    transfer=sale_payload([(product["id"],1)],"transfer",None);transfer.tip_amount=Decimal("3");transfer.tip_method="transfer"
    SaleService.create(db,card);SaleService.create(db,transfer);summary=CashService.summary(db)
    assert summary["tip_card"]=="5.00" and summary["tip_transfer"]=="3.00"
    assert summary["total_collected"]=="100.00" and summary["expected_cash"]=="92.00" and summary["net_total"]=="92.00"
def test_mandatory_service_charge_is_calculated_by_server(db):
    product=ProductService.create(db,product_payload());CashService.open(db,0)
    db.add(PermissionConfig(id=1,include_tip_in_ticket=True,service_charge_percent=10));db.commit()
    sale=SaleService.create(db,sale_payload([(product["id"],1)],"cash","27.50"))
    assert sale.total==Decimal("25.00") and sale.tip_amount==Decimal("2.50") and sale.change_amount==Decimal("0.00")
    summary=CashService.summary(db)
    assert summary["cash"]=="25.00" and summary["tip_cash"]=="2.50" and summary["grand_total"]=="27.50"
def test_cancel_and_transfer_table_items_are_persistent(db):
    product=ProductService.create(db,product_payload());user=User(username="mesero",display_name="Mesero Uno",password_hash="x",role="waiter");db.add(user);db.commit();db.refresh(user)
    source=DiningTableService.create(db,"Mesa 1");target=DiningTableService.create(db,"Mesa 2");source=DiningTableService.add_items(db,source["id"],[SimpleNamespace(product_id=product["id"],quantity=4)])
    source=DiningTableService.cancel_item(db,source["id"],source["items"][0]["id"],1,"Error de captura",user)
    assert source["items"][0]["quantity"]==3 and DiningTableService.cancellations(db,source["id"])[0]["cancelled_by"]=="Mesero Uno"
    transfer=DiningTableService.transfer_items(db,source["id"],target["id"],[SimpleNamespace(item_id=source["items"][0]["id"],quantity=2)],user)
    assert transfer["source"]["items"][0]["quantity"]==1 and transfer["target"]["items"][0]["quantity"]==2

def test_discount_charges_declaration_and_cut_metrics(db):
    product=ProductService.create(db,product_payload());CashService.open(db,"100")
    cashier=User(username="caja",display_name="Caja",password_hash="x",role="cashier");db.add(cashier);db.commit();db.refresh(cashier)
    payload=sale_payload([(product["id"],1)],"cash","20");payload.discount_amount=Decimal("5");payload.discount_reason="Promoción";payload.guest_count=2
    sale=SaleService.create(db,payload)
    table=DiningTableService.create(db,"Mesa cancelada");DiningTableService.cancel(db,table["id"])
    CashService.add_charge(db,"10","Pago de refresco",cashier)
    summary=CashService.summary(db)
    assert sale.subtotal==Decimal("25.00") and sale.total==Decimal("20.00")
    assert summary["discounted_accounts"]==1 and summary["total_discounts"]=="5.00" and summary["cancelled_accounts"]==1 and summary["guests"]==2
    assert summary["average_consumption"]=="20.00" and summary["charges"]=="10.00" and summary["expected_cash"]=="110.00"
    closed=CashService.close(db,"105","20","0")
    assert closed["declared_total"]=="125.00" and closed["cash_variance"]=="-5.00" and closed["net_total"]=="110.00"

def test_discount_requires_reason_and_cannot_exceed_consumption(db):
    product=ProductService.create(db,product_payload());CashService.open(db,0)
    payload=sale_payload([(product["id"],1)],"card",None);payload.discount_amount=Decimal("5")
    with pytest.raises(PosError,match="motivo"):SaleService.create(db,payload)
    payload.discount_reason="Cortesía";payload.discount_amount=Decimal("30")
    with pytest.raises(PosError,match="superar"):SaleService.create(db,payload)

def test_cash_history_reopen_and_audit(db):
    admin=User(username="admin",display_name="Administrador",password_hash="x",role="admin");db.add(admin);db.commit();db.refresh(admin)
    session=CashService.open(db,"250");CashService.close(db,"250","0","0")
    history=CashService.history(db)
    assert history["total"]==1 and history["items"][0]["id"]==session.id
    reopened=CashService.reopen(db,session.id,admin,"Corregir una venta omitida")
    assert reopened["closed_at"] is None and reopened["reopened_count"]==1 and reopened["last_reopened_by"]=="Administrador"
    with pytest.raises(PosError,match="caja actual"):CashService.reopen(db,session.id,admin,"Segundo intento")
    record_audit(db,admin,"cash.reopen","cash_session",session.id,{"reason":"Corregir una venta omitida"})
    audits=list_audits(db)
    assert audits["total"]==1 and audits["items"][0]["action"]=="cash.reopen" and audits["items"][0]["details"]["reason"]=="Corregir una venta omitida"

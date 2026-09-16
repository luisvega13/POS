from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from app.services.ticket_service import WIDTH,cash_ticket,columns,grouped_items,item_header,item_lines,sale_ticket,table_account_ticket

def test_columns_never_exceed_paper_width():
    assert len(columns("TOTAL","$1,234.00"))<=WIDTH
    assert all(len(line)<=WIDTH for line in item_lines("Producto con un nombre extremadamente largo",12,Decimal("1234.50")))
def test_item_columns_keep_quantity_and_total_aligned():
    header=item_header();cheap=item_lines("Coca",1,Decimal("25"))[0];expensive=item_lines("Pizza",12,Decimal("1234.50"))[0]
    assert len(header)==len(cheap)==len(expensive)==WIDTH
    assert cheap.endswith("$25.00") and expensive.endswith("$1,234.50")
    assert cheap[:16].strip()=="Coca" and cheap[16:21].strip()=="1"
    assert expensive[:16].strip()=="Pizza" and expensive[16:21].strip()=="12"
def test_sale_ticket_contains_historical_data():
    sale=SimpleNamespace(folio="000123",created_at=datetime(2026,8,31,20,35),subtotal=Decimal("130"),total=Decimal("130"),payment_method="cash",amount_received=Decimal("200"),change_amount=Decimal("70"),items=[SimpleNamespace(product_name="Coca Cola",quantity=2,subtotal=Decimal("50")),SimpleNamespace(product_name="Hamburguesa",quantity=1,subtotal=Decimal("80"))])
    config=SimpleNamespace(encoding="cp850",character_table=None,business_name="MI NEGOCIO",address="",phone="",ticket_message="¡Gracias por su compra!")
    data=sale_ticket(sale,config)
    assert b"000123" in data and b"$130.00" in data and "Gracias".encode("cp850") in data

def test_table_account_uses_configured_header_phone_message_and_single_total():
    table=SimpleNamespace(name="3",items=[SimpleNamespace(product_name="Pizza",quantity=1,unit_price=Decimal("200"))])
    config=SimpleNamespace(encoding="cp850",character_table=None,business_name="MI NEGOCIO",address="Dirección",phone="4491234567",ticket_message="Vuelva pronto")
    permissions=SimpleNamespace(include_tip_in_ticket=False,include_suggested_tip=True,suggested_tip_percent=10)
    text=table_account_ticket(table,config,permissions).decode("cp850",errors="ignore")
    assert "CUENTA 3" in text and "4491234567" in text and "Vuelva pronto" in text
    assert "CONSUMO" not in text and text.count("TOTAL") == 1

def test_table_account_with_service_charge_keeps_consumption_breakdown():
    table=SimpleNamespace(name="4",items=[SimpleNamespace(product_name="Pizza",quantity=1,unit_price=Decimal("200"))])
    config=SimpleNamespace(encoding="cp850",character_table=None,business_name="MI NEGOCIO",address="",phone="",ticket_message="Gracias")
    permissions=SimpleNamespace(include_tip_in_ticket=True,service_charge_percent=10,include_suggested_tip=False,suggested_tip_percent=10)
    text=table_account_ticket(table,config,permissions).decode("cp850",errors="ignore")
    assert "CONSUMO" in text and "Cargo servicio 10%" in text and "$220.00" in text

def test_repeated_products_are_grouped_on_ticket():
    items=[SimpleNamespace(product_name="Pizza",unit_price=Decimal("180"),quantity=1),SimpleNamespace(product_name="Coca",unit_price=Decimal("25"),quantity=1),SimpleNamespace(product_name="Pizza",unit_price=Decimal("180"),quantity=2),SimpleNamespace(product_name="Coca",unit_price=Decimal("25"),quantity=1)]
    assert grouped_items(items)==[("Pizza",3,Decimal("540")),("Coca",2,Decimal("50"))]
    table=SimpleNamespace(name="5",items=items)
    config=SimpleNamespace(encoding="cp850",character_table=None,business_name="MI NEGOCIO",address="",phone="",ticket_message="Gracias")
    permissions=SimpleNamespace(include_tip_in_ticket=False,include_suggested_tip=False,suggested_tip_percent=10)
    text=table_account_ticket(table,config,permissions).decode("cp850",errors="ignore")
    assert text.count("Pizza")==1 and text.count("Coca")==1
    assert "Pizza               3" in text and "Coca                2" in text

def test_cash_ticket_uses_final_requested_structure():
    summary={"opened_at":"2026-09-15T10:35:00","closed_at":"2026-09-15T18:10:00","opening_amount":"1000.00","operations":10,"cash":"4623.00","card":"65.00","transfer":"0.00","total_sold":"4688.00","tip_cash":"100.00","tip_card":"70.00","tip_transfer":"0.00","total_tips":"170.00","paid_tips":"70.00","guests":2,"cancelled_accounts":0,"discounted_accounts":2,"total_discounts":"125.00","average_consumption":"468.80","charges":"60.00","grand_total":"4858.00","total_collected":"5623.00","net_total":"5493.00","declared_cash":"5493.00","declared_card":"135.00","declared_transfer":"0.00","cash_variance":"0.00"}
    config=SimpleNamespace(encoding="cp850",character_table=None,business_name="MI NEGOCIO")
    text=cash_ticket(summary,config).decode("cp850",errors="ignore")
    expected=("Cierre: 2026-09-15 18:10","Total ventas", "$4,688.00","Cuentas con descuento","Total descontado", "$125.00","Efectivo total","$5,623.00","Propinas pagadas","$70.00","Total                  $5,493.00","DECLARACION DEL CAJERO","Sobrante o faltante")
    assert all(value in text for value in expected)
    assert text.index("Efectivo total")<text.index("DECLARACION DEL CAJERO")<text.index("Sobrante o faltante")
    assert "Gerente" not in text and "Cajero" not in text

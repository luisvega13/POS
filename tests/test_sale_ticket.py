from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from app.services.ticket_service import WIDTH,columns,item_lines,sale_ticket

def test_columns_never_exceed_paper_width():
    assert len(columns("TOTAL","$1,234.00"))<=WIDTH
    assert all(len(line)<=WIDTH for line in item_lines("Producto con un nombre extremadamente largo",12,Decimal("1234.50")))
def test_sale_ticket_contains_historical_data():
    sale=SimpleNamespace(folio="000123",created_at=datetime(2026,8,31,20,35),subtotal=Decimal("130"),total=Decimal("130"),payment_method="cash",amount_received=Decimal("200"),change_amount=Decimal("70"),items=[SimpleNamespace(product_name="Coca Cola",quantity=2,subtotal=Decimal("50")),SimpleNamespace(product_name="Hamburguesa",quantity=1,subtotal=Decimal("80"))])
    config=SimpleNamespace(encoding="cp850",character_table=None,business_name="MI NEGOCIO",address="",phone="",ticket_message="¡Gracias por su compra!")
    data=sale_ticket(sale,config)
    assert b"000123" in data and b"$130.00" in data and "Gracias".encode("cp850") in data

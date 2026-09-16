from datetime import datetime
from decimal import Decimal
from app.printer.ticket_builder import TicketBuilder

WIDTH=32
PRODUCT_WIDTH,QTY_WIDTH,TOTAL_WIDTH=16,5,11
def pesos(value): return f"${Decimal(value):,.2f}"
def fit(value,width):
    text=str(value)
    return text if len(text)<=width else text[:max(0,width-1)]+"…"
def columns(left,right,width=WIDTH):
    right=str(right); room=max(1,width-len(right)-1)
    return f"{fit(left,room):<{room}} {right:>{len(right)}}"
def item_lines(name,quantity,total,width=WIDTH):
    product_width=width-QTY_WIDTH-TOTAL_WIDTH
    words=name.split(); lines=[]; current=""
    for word in words:
        candidate=(current+" "+word).strip()
        if len(candidate)>product_width and current: lines.append(current); current=word
        else: current=candidate
    lines.append(current or name[:product_width])
    result=[f"{fit(lines[0],product_width):<{product_width}}{str(quantity):>{QTY_WIDTH}}{pesos(total):>{TOTAL_WIDTH}}"]
    result.extend(f"{fit(line,product_width):<{product_width}}{'':>{QTY_WIDTH}}{'':>{TOTAL_WIDTH}}" for line in lines[1:])
    return result

def item_header(width=WIDTH):
    product_width=width-QTY_WIDTH-TOTAL_WIDTH
    return f"{'Producto':<{product_width}}{'Cant.':>{QTY_WIDTH}}{'Total':>{TOTAL_WIDTH}}"

def grouped_items(items):
    groups={}
    for item in items:
        unit_price=Decimal(item.unit_price) if hasattr(item,"unit_price") else Decimal(item.subtotal)/item.quantity
        key=(item.product_name,unit_price)
        quantity,total=groups.get(key,(0,Decimal("0")))
        line_total=Decimal(item.subtotal) if hasattr(item,"subtotal") else unit_price*item.quantity
        groups[key]=(quantity+item.quantity,total+line_total)
    return [(name,quantity,total) for (name,_), (quantity,total) in groups.items()]

def base_builder(config):
    b=TicketBuilder(config.encoding).initialize()
    if config.character_table is not None: b.character_table(config.character_table)
    return b
def sale_ticket(sale,config,permissions=None):
    b=base_builder(config).align_center().bold(True).text(config.business_name or "MI NEGOCIO")
    if config.address: b.bold(False).text(config.address)
    if config.phone: b.text(config.phone)
    b.bold(True).text("TICKET DE VENTA").bold(False).text("").align_left()
    b.text(f"Folio: {sale.folio}").text(sale.created_at.strftime("%d/%m/%Y  %H:%M"))
    b.line(WIDTH).text(item_header()).line(WIDTH)
    for name,quantity,total in grouped_items(sale.items):
        for line in item_lines(name,quantity,total): b.text(line)
    b.line(WIDTH)
    discount=getattr(sale,"discount_amount",Decimal("0")) or Decimal("0")
    if discount:b.text(columns("SUBTOTAL",pesos(sale.subtotal))).text(columns("DESCUENTO",f"-{pesos(discount)}"))
    b.bold(True).text(columns("CONSUMO",pesos(sale.total))).bold(False)
    tip=getattr(sale,"tip_amount",Decimal("0")) or Decimal("0")
    if tip:
        percent=getattr(sale,"service_charge_percent",0) or 0;label=f"Cargo servicio {percent}%" if percent else "Propina"
        b.text(columns(label,pesos(tip))).bold(True).text(columns("TOTAL PAGADO",pesos(sale.total+tip))).bold(False)
    b.text("")
    labels={"cash":"EFECTIVO","card":"TARJETA","transfer":"TRANSFERENCIA"}
    b.text("Pago:").bold(True).text(labels.get(sale.payment_method,sale.payment_method.upper())).bold(False)
    if sale.payment_method=="cash":
        b.text("").text(columns("Recibido:",pesos(sale.amount_received))).text(columns("Cambio:",pesos(sale.change_amount)))
    b.text("").align_center().text(config.ticket_message or "¡Gracias por su compra!").feed(4)
    return b.build()
def table_account_ticket(table,config,permissions=None):
    b=base_builder(config).align_center().bold(True).text(config.business_name or "MI NEGOCIO")
    if config.address:b.bold(False).text(config.address)
    if config.phone:b.bold(False).text(config.phone)
    b.bold(True).text(f"CUENTA {table.name}").bold(False).text("").align_left().text(datetime.now().strftime("%d/%m/%Y  %H:%M"))
    b.line(WIDTH).text(item_header()).line(WIDTH)
    for name,quantity,line_total in grouped_items(table.items):
        for line in item_lines(name,quantity,line_total):b.text(line)
    total=sum((item.unit_price*item.quantity for item in table.items),Decimal("0"))
    if permissions and permissions.include_tip_in_ticket:
        charge=(total*Decimal(permissions.service_charge_percent)/Decimal(100)).quantize(Decimal("0.01"));b.line(WIDTH).bold(True).text(columns("CONSUMO",pesos(total))).bold(False).text(columns(f"Cargo servicio {permissions.service_charge_percent}%",pesos(charge))).bold(True).text(columns("TOTAL",pesos(total+charge))).bold(False)
    else:b.line(WIDTH).bold(True).text(columns("TOTAL",pesos(total))).bold(False)
    if permissions and permissions.include_suggested_tip:
        percent=permissions.suggested_tip_percent;b.text(columns(f"Propina sugerida {percent}%",pesos(total*Decimal(percent)/Decimal(100))))
    b.text("").align_center().text(config.ticket_message or "¡Gracias por su compra!").feed(4)
    return b.build()
def cash_ticket(summary,config):
    closed=summary.get("closed_at");closed_text=closed[0:16].replace("T"," ") if closed else "Pendiente"
    b=base_builder(config).align_center().bold(True).text(config.business_name or "MI NEGOCIO").text("CORTE DE CAJA").bold(False).text("").align_left().text(f"Apertura: {summary['opened_at'][0:16].replace('T',' ')}").text(f"Cierre: {closed_text}").text("")
    b.text(columns("Fondo inicial",pesos(summary["opening_amount"]))).text(columns("Operaciones",summary["operations"])).line(WIDTH)
    b.bold(True).text("VENTAS").bold(False).text(columns("Efectivo",pesos(summary["cash"]))).text(columns("Tarjeta",pesos(summary["card"]))).text(columns("Transferencia",pesos(summary["transfer"]))).text(columns("Total ventas",pesos(summary["total_sold"]))).line(WIDTH)
    b.bold(True).text("PROPINAS").bold(False).text(columns("Efectivo",pesos(summary["tip_cash"]))).text(columns("Tarjeta",pesos(summary["tip_card"]))).text(columns("Transferencia",pesos(summary["tip_transfer"]))).text(columns("Total propinas",pesos(summary["total_tips"]))).line(WIDTH)
    b.text(columns("Comensales",summary["guests"])).text(columns("Cuentas canceladas",summary["cancelled_accounts"])).text(columns("Cuentas con descuento",summary["discounted_accounts"])).text(columns("Total descontado",pesos(summary["total_discounts"]))).text(columns("Consumo promedio",pesos(summary["average_consumption"]))).text(columns("Cargos",pesos(summary["charges"]))).line(WIDTH)
    b.text(columns("Efectivo total",pesos(summary["total_collected"]))).text(columns("Propinas pagadas",pesos(summary["paid_tips"]))).text(columns("Cargos",pesos(summary["charges"]))).bold(True).text(columns("Total",pesos(summary["net_total"]))).bold(False).line(WIDTH)
    b.bold(True).text("DECLARACION DEL CAJERO").bold(False).text(columns("Efectivo",pesos(summary.get("declared_cash") or 0))).text(columns("Tarjeta",pesos(summary.get("declared_card") or 0))).text(columns("Transferencia",pesos(summary.get("declared_transfer") or 0))).line(WIDTH).bold(True).text(columns("Sobrante o faltante",pesos(summary.get("cash_variance") or 0))).bold(False).feed(4)
    return b.build()

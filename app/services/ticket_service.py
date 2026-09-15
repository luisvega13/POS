from decimal import Decimal
from app.printer.ticket_builder import TicketBuilder

WIDTH=32
def pesos(value): return f"${Decimal(value):,.2f}"
def fit(value,width):
    text=str(value)
    return text if len(text)<=width else text[:max(0,width-1)]+"…"
def columns(left,right,width=WIDTH):
    right=str(right); room=max(1,width-len(right)-1)
    return f"{fit(left,room):<{room}} {right:>{len(right)}}"
def item_lines(name,quantity,total,width=WIDTH):
    suffix=f"{quantity}  {pesos(total)}"; room=max(8,width-len(suffix)-1)
    words=name.split(); lines=[]; current=""
    for word in words:
        candidate=(current+" "+word).strip()
        if len(candidate)>room and current: lines.append(current); current=word
        else: current=candidate
    lines.append(current or name[:room])
    result=[f"{fit(lines[0],room):<{room}} {suffix}"]
    result.extend(fit(line,width) for line in lines[1:])
    return result

def base_builder(config):
    b=TicketBuilder(config.encoding).initialize()
    if config.character_table is not None: b.character_table(config.character_table)
    return b
def sale_ticket(sale,config):
    b=base_builder(config).align_center().bold(True).text(config.business_name or "MI NEGOCIO")
    if config.address: b.bold(False).text(config.address)
    if config.phone: b.text(config.phone)
    b.bold(True).text("TICKET DE VENTA").bold(False).text("").align_left()
    b.text(f"Folio: {sale.folio}").text(sale.created_at.strftime("%d/%m/%Y  %H:%M"))
    b.line(WIDTH).text(columns("Producto","Cant. Total")).line(WIDTH)
    for item in sale.items:
        for line in item_lines(item.product_name,item.quantity,item.subtotal): b.text(line)
    b.line(WIDTH).bold(True).text(columns("TOTAL",pesos(sale.total))).bold(False).text("")
    labels={"cash":"EFECTIVO","card":"TARJETA","transfer":"TRANSFERENCIA"}
    b.text("Pago:").bold(True).text(labels.get(sale.payment_method,sale.payment_method.upper())).bold(False)
    if sale.payment_method=="cash":
        b.text("").text(columns("Recibido:",pesos(sale.amount_received))).text(columns("Cambio:",pesos(sale.change_amount)))
    b.text("").align_center().text(config.ticket_message or "¡Gracias por su compra!").feed(4)
    return b.build()
def cash_ticket(summary,config):
    b=base_builder(config).align_center().bold(True).text(config.business_name or "MI NEGOCIO").text("CORTE DE CAJA").bold(False).text("").align_left()
    b.text(f"Apertura: {summary['opened_at'][0:16].replace('T',' ')}")
    if summary.get("closed_at"): b.text(f"Cierre:   {summary['closed_at'][0:16].replace('T',' ')}")
    b.line(WIDTH).text(columns("Fondo inicial",pesos(summary["opening_amount"]))).text(columns("Operaciones",summary["operations"]))
    b.text(columns("Efectivo",pesos(summary["cash"]))).text(columns("Tarjeta",pesos(summary["card"]))).text(columns("Transferencia",pesos(summary["transfer"]))).line(WIDTH)
    b.bold(True).text(columns("TOTAL VENDIDO",pesos(summary["total_sold"]))).bold(False).text(columns("Efectivo esperado",pesos(summary["expected_cash"]))).feed(4)
    return b.build()

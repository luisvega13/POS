import re

from app.auth import get_permissions


ESC_POS_COMMANDS=re.compile(rb"\x1b@|\x1b[aEdt].|\x1d!.",re.DOTALL)


def virtual_ticket(data:bytes,encoding:str)->str:
    """Convierte el trabajo ESC/POS real en una vista previa textual legible."""
    clean=ESC_POS_COMMANDS.sub(b"",data).replace(b"\x00",b"")
    return clean.decode(encoding,errors="replace").strip()


def deliver_ticket(request,db,data:bytes,encoding:str,printed_message:str):
    if get_permissions(db).developer_mode:
        return {"success":True,"message":"Ticket virtual generado · Modo desarrollador activo","print_success":None,"virtual_ticket":virtual_ticket(data,encoding)}
    sent=request.app.state.printer.print_ticket(data)
    return {"success":True,"message":printed_message,"print_success":True,"bytes_sent":sent}

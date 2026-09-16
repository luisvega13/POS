from app.printer.ticket_builder import TicketBuilder
from app.services.print_service import virtual_ticket


def test_virtual_ticket_removes_escpos_commands_and_preserves_text():
    data=(TicketBuilder("cp850").initialize().align_center().bold(True).text("CAFÉ Ñ").bold(False).feed(4).build())
    preview=virtual_ticket(data,"cp850")
    assert preview=="CAFÉ Ñ"
    assert "\x1b" not in preview


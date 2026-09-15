from app.printer.printer_service import ThermalPrinterService


def test_printer_name_from_level_2_dictionary():
    row = {"pServerName": None, "pPrinterName": "POS-58", "Status": 0}
    assert ThermalPrinterService._printer_name(row) == "POS-58"


def test_printer_name_from_legacy_tuple():
    assert ThermalPrinterService._printer_name((0, "description", "POS-58", "comment")) == "POS-58"


def test_printer_name_ignores_unknown_shape():
    assert ThermalPrinterService._printer_name({"Status": 0}) == ""

import logging
try:
    import win32print
except ImportError:
    win32print = None

class PrinterError(RuntimeError): pass

class ThermalPrinterService:
    def __init__(self, config): self.config = config
    @staticmethod
    def _api():
        if win32print is None: raise PrinterError("pywin32 no está disponible; instálelo en Windows")
        return win32print
    def get_printers(self):
        api=self._api()
        try:
            rows=api.EnumPrinters(api.PRINTER_ENUM_LOCAL|api.PRINTER_ENUM_CONNECTIONS,None,2)
            try: default=api.GetDefaultPrinter()
            except Exception: default=""
            # pywin32 puede devolver diccionarios para level=2 (versiones
            # actuales) o tuplas para niveles/versiones antiguos.
            names=sorted(
                {name for row in rows if (name := self._printer_name(row))},
                key=str.casefold,
            )
            return [{"name":n,"default":n==default} for n in names]
        except Exception as exc:
            logging.exception("No se pudieron enumerar las impresoras")
            raise PrinterError("No se pudieron consultar las impresoras de Windows") from exc
    @staticmethod
    def _printer_name(row):
        if isinstance(row, dict):
            return str(row.get("pPrinterName") or row.get("PrinterName") or "")
        if isinstance(row, (tuple, list)) and len(row) > 2:
            return str(row[2])
        return ""
    def get_selected_printer(self): return self.config.load().get("printer_name","")
    def printer_exists(self,name): return any(x["name"]==name for x in self.get_printers())
    def set_printer(self,name):
        if not name or not self.printer_exists(name): raise PrinterError("La impresora seleccionada no está instalada en Windows")
        self.config.set_printer(name); logging.info("Impresora seleccionada: %s",name)
    def send_raw(self,data: bytes):
        api=self._api(); name=self.get_selected_printer()
        if not name: raise PrinterError("Seleccione una impresora antes de imprimir")
        if not data: raise PrinterError("El trabajo de impresión está vacío")
        handle=None; doc=False; page=False
        try:
            handle=api.OpenPrinter(name)
            api.StartDocPrinter(handle,1,("Ticket térmico",None,"RAW")); doc=True
            api.StartPagePrinter(handle); page=True
            written=int(api.WritePrinter(handle,data))
            if written != len(data): raise PrinterError(f"Windows aceptó {written} de {len(data)} bytes")
            logging.info("Trabajo enviado al spooler: impresora=%s bytes=%d",name,written)
            return written
        except PrinterError: raise
        except Exception as exc:
            logging.exception("Error de impresión en %s",name)
            raise PrinterError("No se pudo enviar el trabajo a la impresora seleccionada") from exc
        finally:
            if handle is not None:
                if page:
                    try: api.EndPagePrinter(handle)
                    except Exception: logging.exception("Error cerrando página")
                if doc:
                    try: api.EndDocPrinter(handle)
                    except Exception: logging.exception("Error cerrando documento")
                try: api.ClosePrinter(handle)
                except Exception: logging.exception("Error cerrando impresora")
    def print_ticket(self,data): return self.send_raw(data)

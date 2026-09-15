"""Comandos validados contra el 58MM Printer Programmer Manual."""
ESC, GS, LF = b"\x1b", b"\x1d", b"\x0a"
INITIALIZE = ESC + b"@"
ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT = ESC+b"a\x00", ESC+b"a\x01", ESC+b"a\x02"
BOLD_OFF, BOLD_ON = ESC+b"E\x00", ESC+b"E\x01"
SIZE_NORMAL, SIZE_DOUBLE_WIDTH = GS+b"!\x00", GS+b"!\x10"
SIZE_DOUBLE_HEIGHT, SIZE_DOUBLE = GS+b"!\x01", GS+b"!\x11"

def feed(lines: int) -> bytes:
    if not isinstance(lines, int) or not 0 <= lines <= 255:
        raise ValueError("La alimentación debe estar entre 0 y 255 líneas")
    return ESC + b"d" + bytes((lines,))

def character_table(table: int) -> bytes:
    """ESC t n; no se envía automáticamente sin validación física."""
    if table not in {*range(6), *range(16, 20), 255}:
        raise ValueError("Tabla de caracteres no admitida por el manual")
    return ESC + b"t" + bytes((table,))

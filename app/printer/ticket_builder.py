from . import commands

class TicketBuilder:
    """Constructor encadenable de tickets RAW."""
    def __init__(self, encoding: str = "cp850"):
        self.encoding, self._parts = encoding, []
    def initialize(self): self._parts.append(commands.INITIALIZE); return self
    def character_table(self, table): self._parts.append(commands.character_table(table)); return self
    def align(self, value: str):
        options={"left":commands.ALIGN_LEFT,"center":commands.ALIGN_CENTER,"right":commands.ALIGN_RIGHT}
        if value not in options: raise ValueError("Alineación no válida")
        self._parts.append(options[value]); return self
    def align_left(self): return self.align("left")
    def align_center(self): return self.align("center")
    def align_right(self): return self.align("right")
    def bold(self, enabled=True): self._parts.append(commands.BOLD_ON if enabled else commands.BOLD_OFF); return self
    def size(self, value="normal"):
        options={"normal":commands.SIZE_NORMAL,"double_width":commands.SIZE_DOUBLE_WIDTH,"double_height":commands.SIZE_DOUBLE_HEIGHT,"double":commands.SIZE_DOUBLE}
        if value not in options: raise ValueError("Tamaño no válido")
        self._parts.append(options[value]); return self
    def normal_size(self): return self.size("normal")
    def double_width(self): return self.size("double_width")
    def double_height(self): return self.size("double_height")
    def double_size(self): return self.size("double")
    def text(self, value: str, newline=True):
        self._parts.append(value.encode(self.encoding, errors="replace"))
        if newline: self._parts.append(commands.LF)
        return self
    def line(self, width=32, char="-"):
        if width < 1 or len(char) != 1: raise ValueError("Línea no válida")
        return self.text(char*width)
    def feed(self, lines=1): self._parts.append(commands.feed(lines)); return self
    def raw(self, data: bytes): self._parts.append(bytes(data)); return self
    def build(self): return b"".join(self._parts)

import pytest
from app.printer import commands
from app.printer.ticket_builder import TicketBuilder

def test_initialize(): assert TicketBuilder().initialize().build() == b"\x1b\x40"
def test_bold_on_off(): assert TicketBuilder().bold(True).bold(False).build() == b"\x1b\x45\x01\x1b\x45\x00"
@pytest.mark.parametrize(("name","expected"),[("left",b"\x1b\x61\x00"),("center",b"\x1b\x61\x01"),("right",b"\x1b\x61\x02")])
def test_alignment(name,expected): assert TicketBuilder().align(name).build() == expected
@pytest.mark.parametrize(("name","value"),[("normal",0),("double_width",16),("double_height",1),("double",17)])
def test_sizes(name,value): assert TicketBuilder().size(name).build() == b"\x1d\x21"+bytes((value,))
def test_feed(): assert TicketBuilder().feed(3).build() == b"\x1b\x64\x03"
@pytest.mark.parametrize("table",[0,1,2,3,4,5,16,17,18,19,255])
def test_documented_character_tables(table):
    assert TicketBuilder().character_table(table).build() == b"\x1b\x74"+bytes((table,))
def test_cp850(): assert TicketBuilder("cp850").text("ñ").build() == "ñ".encode("cp850")+b"\x0a"
def test_invalid_values():
    with pytest.raises(ValueError): TicketBuilder().align("diagonal")
    with pytest.raises(ValueError): commands.feed(256)
    with pytest.raises(ValueError): TicketBuilder().character_table(6)

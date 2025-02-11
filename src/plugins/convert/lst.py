from socx import command, LstConverter

@command()
def cli():
    """Convert symbol tables from an LST file to SystemVerilog covergroups."""
    LstConverter().convert()

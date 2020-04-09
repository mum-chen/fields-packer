import sys
sys.path.append("../../")

import os
import csv
import re
from fields_packer import Field, Block
from fields_packer import ParserBase, ParserWithNameDict
from fields_packer import CGeneratorBase, CUnionBase

class CsvParserLike():
    """
    This class should be mixed with subclass of ParserBase()
    """
    TYPE_EMPTYLINE = "EMPYY"
    TYPE_COMMENT   = "COMMENT"
    TYPE_ADDRESS   = "ADDRESS"
    TYPE_FIELD     = "FIELD"
    TYPE_UNKNOW    = "UNKNOW"

    def __init__(self, csv_file):
        self._csv = csv_file

    def cal_row_type(self, row):
        if len(row) == row.count(""):
            return self.TYPE_EMPTYLINE

        if row[0] == "#":
            return self.TYPE_COMMENT

        s = row[1]
        if re.match("^# addr=.*$", s):
            return self.TYPE_ADDRESS

        if re.match("\[.*\]$", s):
            return self.TYPE_FIELD

        return self.TYPE_UNKNOW

    def extract_addr(self, row):
        return Field.extract_hex(row[1])

    def add_field(self, addr, row):
        bits, shift = Field.extract_range(row[1])
        name = row[2]
        f = Field.new_field(
            name = name,
            addr = addr,
            bits = bits,
            shift = shift,
            source = str(row)
        )
        self._add_field(f)

class SimpleCsvParser(ParserBase, CsvParserLike):
    """
    You can implement your own _parser() with _add_field().
    """
    def __init__(self, csv_file):
        ParserBase.__init__(self,
            gname = "Simple",
            gdesc = "This is a simple demo")
        CsvParserLike.__init__(self, csv_file)

    def _parser(self):
        with open(self._csv, "r") as csvfile:
            spamreader = csv.reader(csvfile)
            addr = None
            for row in spamreader:
                row_type = self.cal_row_type(row)
                if row_type == self.TYPE_ADDRESS:
                    addr = self.extract_addr(row)
                elif row_type == self.TYPE_FIELD:
                    self.add_field(addr, row)
                # else ignore


class ComplexCsvParser(ParserWithNameDict, CsvParserLike):
    """
    You can override some functions to build group.
    - bcreator: modify default function for block
    - _find_block_name(): rename block

    You can find the difference between `simple.c` and `complex.c`
    """

    def __init__(self, csv_file):
        def addr_parser(block):
            return "0x{:04x}".format(block._addr)

        """
        Function addr_parser() changes the default behavior of block.address().
        This option is helpful when you have more than one items in block._addr.
        """
        bcreator = Block.BlockCreator(
            addr_parser = addr_parser
        )

        ParserWithNameDict.__init__(self,
            gname = "AddressedBlock",
            gdesc = "This demo shows how to use block creator",
            bcreator = bcreator)
        CsvParserLike.__init__(self, csv_file)

    def _parser(self):
        with open(self._csv, "r") as csvfile:
            spamreader = csv.reader(csvfile)
            addr = None
            for row in spamreader:
                row_type = self.cal_row_type(row)
                if row_type == self.TYPE_ADDRESS:
                    addr = self.extract_addr(row)
                    # XXX: record block here
                    self._register_block_name(addr, row[2])
                elif row_type == self.TYPE_FIELD:
                    self.add_field(addr, row)
                # else ignore

class RawCsvParser(ParserBase, CsvParserLike):
    """
    You can implement your own _parser() with _group.

    This way requires you know the details of Field, Block and Group,
    which are defined in core.py
    """

    def __init__(self, csv_file):
        ParserBase.__init__(self,
            gname = "Raw",
            gdesc = "This is a raw demo")
        CsvParserLike.__init__(self, csv_file)

    def _parser(self):
        """
        You can implement your own _parser() here.
        """

        with open(self._csv, "r") as csvfile:
            spamreader = csv.reader(csvfile)
            addr = None

            block = None
            for row in spamreader:
                row_type = self.cal_row_type(row)
                if row_type == self.TYPE_ADDRESS:
                    addr = Field.extract_hex(row[1])
                    name = row[2]
                    block = Block(name = name, address = addr)
                    self._group.add_block(block)
                elif row_type == self.TYPE_FIELD:
                    bits, shift = Field.extract_range(row[1])
                    name = row[2]
                    f = Field.new_field(
                        name = name,
                        addr = addr,
                        bits = bits,
                        shift = shift,
                        source = str(row)
                    )
                    block.add_field(f)
                # else ignore

"""
You can define your own c-union creator like below.
"""
class DemoCUnion(CUnionBase):
    def _gen_setter(self):
        """
        You can override default setter function.
        In this function you can access block info.
        """
        return "/* DEMO impl setter for block: {name}*/".format(
            name = self._block.name()
        )

    def _gen_getter(self):
        """
        You can do nothing with this function also.
        """
        return ""

"""
Way 1:
    You can create subclass of CGeneratorBase.
    generator = SubClassCGeneratorBase()

Way 2:
    You can also use CGeneratorBase directly.
    generator = CGeneratorBase(group, DemoCUnion)
"""
class DemoCGenerator(CGeneratorBase):
    def __init__(self, group):
        # setup generator with custom CUnion.
        super().__init__(group, DemoCUnion)


class DemoPacker():
    @classmethod
    def _gen_demo(cls, parser, generator, csv, opath):
        # get instance of Parser.
        parser = parser(csv)
        # parse the csv file and get the result.
        group = parser.gen_group()
        # setup Generator with group.
        gen = generator(group)
        # generate code with group.
        code = gen.generate()
        # output codes
        with open(opath, "w") as f:
            f.write(code)

    @classmethod
    def gen_demos(cls, csv_file, obase):
        """
        Run demos
        """
        cls._gen_demo(SimpleCsvParser, DemoCGenerator,
                csv_file, os.path.join(obase, "simple.c"))
        cls._gen_demo(ComplexCsvParser, DemoCGenerator,
                csv_file, os.path.join(obase, "complex.c"))
        cls._gen_demo(RawCsvParser, DemoCGenerator,
                csv_file, os.path.join(obase, "raw.c"))

ifile = sys.argv[1] # input csv_file
obase = sys.argv[2] # output dir
DemoPacker.gen_demos(ifile, obase)

import sys
sys.path.append("../../")

import os
import csv
import re

from fields_packer import Field, Block, Group
from fields_packer import ParserWithNameDict
from fields_packer import CGeneratorBase, CUnionBase, CUnionRaw

"""
This is a basic class for other parsers.
"""
class CsvParser(ParserWithNameDict):
    TYPE_EMPTYLINE = "EMPYY"
    TYPE_COMMENT   = "COMMENT"
    TYPE_ADDRESS   = "ADDRESS"
    TYPE_FIELD     = "FIELD"
    TYPE_UNKNOW    = "UNKNOW"

    def __init__(self, csv_file, *args, **kw):
        super().__init__(*args, **kw)
        self._csv = csv_file

    def cal_row_type(self, row):
        if len(row) == row.count(""):
            return self.TYPE_EMPTYLINE

        if row[0].startswith("#"):
            return self.TYPE_COMMENT

        s = row[1]
        if re.match("^# addr=.*$", s):
            return self.TYPE_ADDRESS

        if re.match("\[.*\]$", s):
            return self.TYPE_FIELD

        return self.TYPE_UNKNOW

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


"""
The classes below show a demo for generating continuous registers.

This demo packs generated unions into a single structure.
You can find how to use this structure in `csrc/test.c`
"""
class BusMapCsvParser(CsvParser):
    def __init__(self, csv_file):
        super().__init__(
            csv_file,
            gname = "BusMap",
            gdesc = "continuous registers")

    def extract_addr(self, row):
        return Field.extract_hex(row[1])

    def _parser(self):
        with open(self._csv, "r") as csvfile:
            spamreader = csv.reader(csvfile)
            addr = None
            for row in spamreader:
                row_type = self.cal_row_type(row)
                if row_type == self.TYPE_ADDRESS:
                    addr = self.extract_addr(row)
                    self._register_block_name(addr, row[2])
                elif row_type == self.TYPE_FIELD:
                    self.add_field(addr, row)
                # else ignore


class BusMapUnion(CUnionRaw):
    C_TYPE_FIELDS = "uint16_t"


class BusMapGenerator(CGeneratorBase):
    def __init__(self, group):
        super().__init__(group, BusMapUnion)

    def _gen_whole_bus(self, unions):
        head = "struct bus_map {"
        body = "\t{type} {name};"
        tail = "};"

        codes = list()
        codes.append(head)
        for u in unions:
            name = u.name()
            codes.append(body.format(type = name.upper(), name = name.lower()))
        codes.append(tail)
        return "\n".join(codes)

    def generate(self):
        code = super().generate()
        whole_bus = self._gen_whole_bus(self._unions)
        return "\n".join([code, whole_bus])


"""
The classes below show a demo for generating discontinuous registers.

You can also access those registers by the same way as `BusMap`, but
you have to fill up gaps between registers.

We support some helpers to access fields in `csrc/register.h`
You can find how to use those unions and helpers in `csrc/test.c`
"""
class BusCsvParser(CsvParser):
    def __init__(self, csv_file):
        super().__init__(
            csv_file,
            gname = "Bus",
            gdesc = "discontinuous registers",
            bcreator = Block.BlockCreator(
                addr_parser = lambda b: "0x{:04x}".format(b._addr)),
        )

    def extract_addr(self, row):
        return Field.extract_hex(row[1])

    def _parser(self):
        with open(self._csv, "r") as csvfile:
            spamreader = csv.reader(csvfile)
            addr = None
            for row in spamreader:
                row_type = self.cal_row_type(row)
                if row_type == self.TYPE_ADDRESS:
                    addr = self.extract_addr(row)
                    self._register_block_name(addr, row[2])
                elif row_type == self.TYPE_FIELD:
                    self.add_field(addr, row)
                # else ignore


class BusUnion(CUnionBase):
    def _gen_setter(self):
        tmpl = "\n".join([
            "static inline void __reg_write_{name}(uint32_t val)",
            "{{",
                "\t*((volatile uint32_t *){addr}) = val;",
            "}}",
            "",
        ])

        return tmpl.format(
            name = self._block.name(),
            addr = self._block.address()
        )

    def _gen_getter(self):
        tmpl = "\n".join([
            "static inline uint32_t __reg_read_{name}(void)",
            "{{",
                "\treturn *((volatile uint32_t *){addr});",
            "}}",
            "",
        ])

        return tmpl.format(
            name = self._block.name(),
            addr = self._block.address()
        )


class BusGenerator(CGeneratorBase):
    def __init__(self, group):
        super().__init__(group, BusUnion)


"""
The classes below show a demo for generating registers have to be accessed
with other functions. We show a way to extern functions and create setter
and getter with those functions.

We support some helpers to access fields in `csrc/register.h`
You can find how to use those unions and helpers in `csrc/test.c`
"""
class PeripheralCsvParser(CsvParser):
    def __init__(self, csv_file):
        def addr_parser(block):
            dev, addr = block._addr
            return "Dev{dev:d}, Addr({addr:04x})".format(
                    dev = dev, addr = addr)

        super().__init__(
            csv_file,
            gname = "Peripheral",
            gdesc = "registers behind peripherals",
            bcreator = Block.BlockCreator(addr_parser = addr_parser),
        )

    def extract_addr(self, row):
        addr = row[1]
        res = re.findall("0[xX][0-9a-f,A-F]+", addr)
        if res == "":
            raise ValueError("Unknow hex format", res)
        high = res[0]
        low = res[1]
        return int(high, 16), int(low, 16)

    def _parser(self):
        with open(self._csv, "r") as csvfile:
            spamreader = csv.reader(csvfile)
            addr = None
            for row in spamreader:
                row_type = self.cal_row_type(row)
                if row_type == self.TYPE_ADDRESS:
                    addr = self.extract_addr(row)
                    self._register_block_name(addr, row[2])
                elif row_type == self.TYPE_FIELD:
                    self.add_field(addr, row)
                # else ignore


class PeripheralUnion(CUnionBase):
    def _gen_setter(self):
        tmpl = "\n".join([
            "static inline void __reg_write_{name}(uint32_t val)",
            "{{",
                "\tpwrite({dev}, {addr}, val);",
            "}}",
            "",
        ])

        dev, addr = self._block._addr
        return tmpl.format(
            name = self._block.name(),
            dev = dev,
            addr = addr,
        )

    def _gen_getter(self):
        tmpl = "\n".join([
            "static inline uint32_t __reg_read_{name}(void)",
            "{{",
                "\treturn pread({dev}, {addr});",
            "}}",
            "",
        ])

        dev, addr = self._block._addr
        return tmpl.format(
            name = self._block.name(),
            dev = dev,
            addr = addr,
        )


class PeripheralGenerator(CGeneratorBase):
    def __init__(self, group):
        super().__init__(group, PeripheralUnion)

    def generate(self):
        code = super().generate()
        extern = "\n".join([
            "extern void pwrite(uint16_t dev, uint16_t addr, uint32_t val);",
            "extern uint32_t pread(uint16_t dev, uint16_t addr);",
            "",
        ])
        return extern + code

class GenTop():
    @classmethod
    def gen_code(cls, csv, parser, generator):
        parser = parser(csv)
        group = parser.gen_group()

        Group.check_duplicated_name(group)
        gen = generator(group)
        code = gen.generate()

        desc = "/*\n * {}\n */".format(str(group))
        return code, desc

    @classmethod
    def gen_all(cls, output):
        out_file = "reg_all.h"
        path = os.path.join(output, out_file)

        head, tail = CGeneratorBase.once_only_header(out_file)

        configs = (
            ("bus-map.csv", BusMapCsvParser, BusMapGenerator),
            ("bus.csv", BusCsvParser, BusGenerator),
            ("peripheral.csv", PeripheralCsvParser, PeripheralGenerator),
        )

        codes = list()
        codes.append(head)
        for cfg in configs:
            code, desc = cls.gen_code(*cfg)
            codes.append(desc)
            codes.append(code)
        codes.append(tail)

        full_code = "\n".join(codes)
        with open(path, "w") as f:
            f.write(full_code)

GenTop.gen_all("./build/")

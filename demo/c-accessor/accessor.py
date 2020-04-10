import sys
sys.path.append("../../")

import os
import csv
import re

from fields_packer import Field, Block, Group
from fields_packer import ParserWithNameDict
from fields_packer import CGeneratorBase, CUnionBase

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


class AccessorCsvParser(CsvParser):
    def __init__(self, csv_file):
        super().__init__(
            csv_file,
            gname = "Accessor",
            gdesc = "Create setter and getter with fields",
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


class AccessorUnion(CUnionBase):
    TEMPLETE_GETTER = (
"""
static inline uint32_t get_{field}(void)
{{
	{uname} reg = ({uname})reg_read({addr});
	return reg.{field};
}}
""")

    TEMPLETE_SETTER = (
"""
static inline void set_{field}(uint32_t val)
{{
	{uname} reg = ({uname})reg_read({addr});
	reg.{field} = val;
	reg_write({addr}, reg.val);
}}
""")

    def __gen_accessor(self, templete):
        codes = list()
        block = self._block
        fields = block.dump()

        for field in fields:
            code = templete.format(
                field = field.name,
                addr = block.address(),
                uname = self.name(),
            )
            codes.append(code)
        return "\n".join(codes)

    def _gen_setter(self):
        return self.__gen_accessor(self.TEMPLETE_SETTER)

    def _gen_getter(self):
        return self.__gen_accessor(self.TEMPLETE_GETTER)


class AccessorGenerator(CGeneratorBase):
    def __init__(self, group):
        super().__init__(group, AccessorUnion)

    def generate(self):
        code = super().generate()
        extern = "\n".join([
            "#include <stdint.h>",
            "extern void reg_write(uint16_t addr, uint32_t val);",
            "extern uint32_t reg_read(uint16_t addr);",
            "",
        ])
        return extern + code

class GenTop():
    @classmethod
    def gen_all(cls, output):
        csv = "bus.csv"
        out_file = "reg_accessor.h"
        path = os.path.join(output, out_file)
        head, tail = CGeneratorBase.once_only_header(out_file)

        parser = AccessorCsvParser(csv)
        group = parser.gen_group()

        Group.check_duplicated_name(group)
        gen = AccessorGenerator(group)
        code = gen.generate()

        codes = list()
        codes.append(head)
        codes.append(code)
        codes.append(tail)

        full_code = "\n".join(codes)
        with open(path, "w") as f:
            f.write(full_code)

GenTop.gen_all("./build/")

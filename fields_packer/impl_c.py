from .core import Field, Block, Group, GeneratorBase

class CUnionBase():
    """
    Union size: 16bits
    Endianness: littel-endian
    """

    C_TYPE_FIELDS = "uint32_t"

    TEMPLETE_NAME = "R_{block_name}"

    TEMPLETE_RAW_NAME = "union r_{block_name}"

    TEMPLETE_TYPEDEF = "\n".join([
        "typedef {raw_name} {{",
        "{struct}",
        "}} {name};"
    ])

    TEMPLETE_UNION = "\n".join([
            "\tstruct {{",
                "{attrs}",
            "\t}};",
            "\t{c_type} val;",
    ])

    TEMPLETE_ATTRITUBE = "\t\t{c_type} {name}:{bits};\t/*{comment}*/"
    def __init__(self, block: Block):
        # TODO: extract to an arg
        self._max_bits = 16

        self._block = block

    def generate(self):
        comment = self._gen_comment()
        struct = self._gen_structure()
        setter = self._gen_setter()
        getter = self._gen_getter()

        return "\n".join([comment, struct, setter, getter])

    def name(self):
        return self.TEMPLETE_NAME.format(block_name = self._block.name())

    def raw_name(self):
        return self.TEMPLETE_RAW_NAME.format(block_name = self._block.name())

    def _gen_setter(self) -> str:
        """
        You can override this function
        """
        return "/* NotImplemented Block Setter */"

    def _gen_getter(self) -> str:
        """
        You can override this function
        """
        return "/* NotImplemented Block Getter */"

    def _gen_comment(self) -> str:
        return "/* block: {name}({addr}) */".format(
            name = self._block.name(),
            addr = self._block.address()
        )

    def _gen_structure(self) -> str:
        name = self._block.name()
        struct = self.__pack_block()

        return self.TEMPLETE_TYPEDEF.format(
            name = self.name(),
            raw_name = self.raw_name(),
            struct = struct
        )

    def __pack_block(self):
        atmpl = self.TEMPLETE_ATTRITUBE
        def new_field(field):
            comment = field.range()
            return atmpl.format(
                c_type = self.C_TYPE_FIELDS,
                name = field.name,
                bits = field.bits,
                comment = comment
            )

        def unused_field(idx, bits, shift):
            comment = Field.cal_range(bits, shift)
            name = "unused{}".format(idx)
            return atmpl.format(
                c_type = self.C_TYPE_FIELDS,
                name = name,
                bits = bits,
                comment = comment
            )

        block = self._block
        fields = block.dump()

        total_bits = 0
        attrs = list()
        unused_idx = 0
        last_shift = 0

        # generate attributes
        for f in fields:
            if f.shift != last_shift:
                # inject unused attribute to fill the gaps.
                high = f.shift - 1
                low = last_shift
                bits = high - low + 1
                attr = unused_field(unused_idx, bits, low)

                # update global info
                unused_idx += 1
                total_bits += bits
                attrs.append(attr)

            # fill attribute by field
            attr = new_field(f)

            # update global info
            total_bits += f.bits
            attrs.append(attr)
            last_shift = f.shift + f.bits

        if total_bits > self._max_bits:
            raise Exception(
                "The block:{} has too many bits".fromat(self._block.name))
        elif total_bits < self._max_bits:
            # fill the reset of bits
            bits = self._max_bits - total_bits
            low = last_shift
            attr = unused_field(unused_idx, bits, low)
            attrs.append(attr)

        attrs = "\n".join(attrs)

        return self.TEMPLETE_UNION.format(
            attrs = attrs,
            c_type = self.C_TYPE_FIELDS
        )


class CUnionRaw(CUnionBase):
    def _gen_setter(self): return ""
    def _gen_getter(self): return ""


class CGeneratorBase(GeneratorBase):
    def __init__(self, group: Group, create_union = None):
        self._group = group
        self._create_union = create_union or CUnionBase

    def generate(self):
        blocks = self._group.dump()
        unions = list(map(lambda b: self._create_union(b), blocks))
        codes = list(map(lambda u: u.generate(), unions))
        return "\n".join(codes)

    @classmethod
    def once_only_header(cls, hfile_name):
        """
        @input hfile_name: format xxx_xxx.h
        @output (head, tail)
            return macros with #ifndef
        """
        flag = ("__" + hfile_name.replace(".", "_") + "__").upper()
        head = "\n".join([
            "#ifndef {flag}",
            "#define {flag}",
        ]).format(flag = flag)
        tail = "#endif /* {flag} */".format(flag = flag)
        return head, tail

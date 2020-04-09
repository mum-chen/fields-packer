import re
from typing import Sequence, Optional, Callable, Any
from collections import namedtuple

"""
Hierarchy:
              Group          |   Another Group
                ^            |
                |            |
    Block   ...     Block    |
       ^                     |
       |         |           |
Field ... Field  | ......... | ....

- The basic unit is field
- A block contains at least one field.
- A group contains at least one block.
- Blocks in the same gruops have same `parser` and `generator`.
"""

_Field = namedtuple("Field", [
    "name",
    "addr",
    "bitmask",
    "bits",
    "shift",
    "group",
    "default",
    "source",
    "extra",
])


class Field(_Field):
    @classmethod
    def cal_bitmask(cls, bits, shift):
        mask = ((1 << bits) - 1) << shift
        return mask

    @classmethod
    def cal_range(cls, bits, shift):
        low = shift
        high = low + bits - 1
        if bits == 1:
            return "[{}]".format(low)
        else:
            return "[{h}:{l}]".format(h = high, l = low)

    @staticmethod
    def extract_hex(s):
        res = re.findall("0[xX][0-9a-f,A-F]+", s)[0]
        if res == "":
            raise ValueError("Unknow hex format", res)
        return int(res, 16)

    @classmethod
    def extract_range(cls, source):
        '''
        Here we support only have two types of the string:
        - "[x:y]"
        - "[x]"

        return bits, shift
        '''
        num_list = list(
            map(int,
                filter(lambda x: x != "",
                       re.findall("\d*", source))
                ))

        if (len(num_list) not in [1, 2]):
            raise ValueError("Illegal range input:{}".format(source))

        high = num_list[0]
        low = num_list[-1]

        if high < low:
            high, low = low, high

        bits = high - low + 1
        shift = low

        return bits, shift

    @classmethod
    def new_field(cls, name, addr, bits, shift,
            group = None, default = 0, source = None, extra = None):

        bitmask = cls.cal_bitmask(bits, shift)

        return Field(
            name = name.strip(),
            addr = addr,
            bits = bits,
            bitmask = bitmask,
            shift = shift,
            group = group,
            default = default,
            source = source,
            extra = extra,
        )

    def range(self):
        return self.cal_range(self.bits, self.shift)


class BlockCreator():
    """
    This is a helper class for creating Block.
    The create() will set funtions automatically.

    Link to: class Block
    """
    def __init__(self, reverse = False, checker = None, sortby = None, addr_parser = None):
        self._checker = checker
        self._sortby = sortby
        self._parser = addr_parser
        self._reverse = reverse

    def create(self, name, addr, fields = None):
        block = Block(name, addr, fields,
                      checker = self._checker,
                      sortby = self._sortby,
                      parse_addr = self._parser)

        block.reverse = self._reverse
        return block

class Block():
    BlockCreator = BlockCreator

    class IllegalFieldAddr(ValueError): pass

    BlockCheckerType = Callable[['Block', Field], bool]
    BlockSortbyType = Callable[[Field], Any]
    BlockParseAddress = Callable[['Block'], Any]

    def __init__(
            self,
            name: str,
            address: Any,
            fields: Optional[Sequence[Field]] = None,
            checker: Optional[BlockCheckerType] = None,
            sortby: Optional[BlockSortbyType] = None,
            parse_addr: Optional[BlockParseAddress] = None):

        self._name = name.strip()
        self._addr = address
        self._fields = (fields or []).copy()
        self.__sortby = sortby
        self.__checker = checker
        self.__parse_addr = parse_addr

        self.reverse = False

    def __str__(self):
        return "{name}@({addr})".format(name = self._name, addr = self._addr)

    def show(self):
        print(self)
        self.sort()
        for f in self._fields:
            print(f)

    def name(self):
        return self._name

    def address(self):
        if self.__parse_addr:
            return self.__parse_addr(self)
        else:
            return self._addr

    def add_field(self, field: Field) -> None:
        if not self.check(field):
            err = "Error with adding field: block._addr:{} field.addr: {}".format(
                self._addr, field.addr)
            raise self.IllegalFieldAddr(err)

        self._fields.append(field)

    def dump(self) -> Sequence[Field]:
        self.sort()
        return self._fields.copy()

    def sort(self) -> None:
        if self.__sortby:
            self._fields = sorted(
                    self._fields, reverse = self.reverse,
                    key=lambda f: self.__sortby(f))
        else:
            self._fields = sorted(
                    self._fields, reverse = self.reverse,
                    key=lambda f: f.shift)

    def check(self, field: Field) -> bool:
        if self.__checker:
            return self.__checker(self, field)
        else:
            return self._addr == field.addr


class Group():
    class IllegalBlock(ValueError): pass

    GroupCheckerType = Callable[['Group', Block], bool]
    GroupSortbyType = Callable[[Block], Any]

    def __init__(
            self,
            name: str,
            gdesc: Any = None,
            blocks: Optional[Sequence[Block]] = None,
            checker: Optional[GroupCheckerType] = None,
            sortby: Optional[GroupSortbyType] = None):
        self._name = name
        self._desc = gdesc
        self._blocks = (blocks or []).copy()
        self.__sortby = sortby
        self.__checker = checker

        self.reverse = False

    def __str__(self):
        return "Group{name}: {desc}".format(
                name = self._name,
                desc = self._desc)

    def add_block(self, block: Block):
        if not self._check(block):
            raise self.IllegalBlock("Error with adding block")

        self._blocks.append(block)

    def dump(self) -> Sequence[Block]:
        self._sort()
        return self._blocks.copy()

    def show(self) -> None:
        print(self)
        self._sort()
        for b in self._blocks:
            b.show()

    def _sort(self) -> None:
        if self.__sortby:
            self._blocks = sorted(
                self._blocks, reverse = self.reverse,
                key=lambda b: self.__sortby(b))
        else:
            self._blocks = sorted(
                self._blocks, reverse = self.reverse,
                key=lambda b: b.address())

    def _check(self, block: Block) -> bool:
        if self.__checker:
            return self.__checker(self, block)
        else:
            return True


class GeneratorBase():
    def __init__(self, source):
        pass

    def generate(self) -> str:
        raise NotImplementedError

class ParserBase():
    def __init__(self,
            gname,
            gdesc = None,
            gchecker = None,
            gsortby = None,

            bcreator = None
        ):

        self._group = Group(
            gname, gdesc,
            checker = gchecker,
            sortby = gsortby
        )
        self._bcreator = bcreator or Block.BlockCreator()

        self._last_block = None

        self._is_parsed = False

    def gen_group(self):
        if not self._is_parsed:
            self._is_parsed = True
            self._parser()
        return self._group

    def __create_new_block(self, addr):
        """
        create block and add new block into group.

        Link to: _find_block_name()
        """
        bname = self._find_block_name(addr)
        block = self._bcreator.create(bname, addr)
        self._group.add_block(block)
        return block

    def _find_block_name(self, addr) -> str:
        """
        You can override this function for generating block names
        automatically. This function is typically called in _add_field().

        Link to: _add_field()
        """
        return str(addr)

    def _add_field(self, field):
        """
        You only need to add field without considering errands with block
        and group. The group switches to next and add block when adress is
        changed.

        Link to: _find_block_name()
        """
        block = self._last_block
        if block is not None:
            try:
                block.add_field(field)
            except Block.IllegalFieldAddr:
                """
                find next block
                """
                block = self.__create_new_block(field.addr)
                block.add_field(field)
        else:
            block = self.__create_new_block(field.addr)
            block.add_field(field)

        self._last_block = block

    def _parser(self):
        """
        Way 1:
          You can manipulate group(self._group) directly.
          Things with Field, Block and Group are in this source also.

        Way 2:
          You can just add field with add_field() by ignoring details.

          In this way, you might need to override some functions.
          - _find_block_name(): find block name when creating new block.

        NOTE:
          We don't recommend you use diffrent ways in one implementation,
          but it's up to you.

        """
        raise NotImplementedError

class ParserWithNameDict(ParserBase):
    def __init__(self, *arg, **kw):
        super().__init__(*arg, **kw)
        self._name_dict = dict()

    def _register_block_name(self, addr: Any, name: str) -> None:
        if self._name_dict.get(addr, None) is not None:
            raise ValueError(
                "Duplicated block address input: {}, {}".format(addr, name))
        self._name_dict[addr] = name.strip()

    def _find_block_name(self, addr: Any):
        name = self._name_dict.get(addr, None)
        if not name:
            raise ValueError("Not found block name for {}".format(addr))
        return name

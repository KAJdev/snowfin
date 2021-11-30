__all__ = (
    'Color',
    'Colour',
)

class Color:
    """
    Color class for embeds.
    """

    __slots__ = ('value',)

    r = property(lambda self: self.value >> 16 & 0xFF)
    g = property(lambda self: self.value >> 8 & 0xFF)
    b = property(lambda self: self.value & 0xFF)

    def __init__(self, value: int):
        if not isinstance(value, int):
            raise TypeError(f'Expected int parameter, received {value.__class__.__name__} instead.')

        self.value: int = value

    def __str__(self) -> str:
        return f'#{self.value:0>6x}'

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f'<Color value={self.value}>'

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int):
        """
        Creates a color from RGB values.
        """
        return cls(int(r) << 16 | int(g) << 8 | int(b))

    @classmethod
    def from_hex(cls, hex_code: str):
        """
        Creates a color from a hex code.
        """
        return cls.from_rgb(*[int(hex_code[i:i+2], 16) for i in (0, 2, 4)])

Colour = Color
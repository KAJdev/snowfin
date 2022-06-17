from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import typing

from .color import Color

__all__ = ("Embed", "EmbedAuthor", "EmbedField", "EmbedFooter")


@dataclass
class EmbedField:
    """Represents an embed field.

    Parameters
    ----------
    name : str
        name of the field
    value : str
        value of the field
    inline : bool
        whether or not this field should display inline
    """

    name: str
    value: str
    inline: bool = False

    def to_dict(self) -> dict[str, typing.Union[str, bool]]:
        """Turns the EmbedField into a dictionary

        Returns
        -------
        dict[str, typing.Union[str, bool]]
            the dictionary made from the attributes
        """
        return self.__dict__


@dataclass
class EmbedAuthor:
    """Represents an embed author.

    Parameters
    ----------
    name : str
        name of author
    url : typing.Optional[str]
        url of author
    icon_url : typing.Optional[str]
        url of author icon (only supports http(s) and attachments)
    """

    name: str
    url: typing.Optional[str] = None
    icon_url: typing.Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        """Turns the EmbedField into a dictionary

        Returns
        -------
        dict[str, str]
            the dictionary made from the attributes
        """
        return {key: value for key, value in self.__dict__.items() if value}


@dataclass
class EmbedFooter:
    """Represents an embed footer.

    Parameters
    ----------
    text : str
        footer text
    icon_url : typing.Optional[str]
        url of footer icon (only supports http(s) and attachments)
    """

    text: str
    icon_url: typing.Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        """Turns the EmbedField into a dictionary

        Returns
        -------
        dict[str, str]
            the dictionary made from the attributes
        """
        return {key: value for key, value in self.__dict__.items() if value}


@dataclass
class Embed:
    """Represents an embed

    Parameters
    ----------
    title : typing.Optional[str]
        title of embed
    description : typing.Optional[str]
        description of embed
    url : typing.Optional[str]
        url of embed
    timestamp : typing.Optional[typing.Union[int, datetime]]
        timestamp of embed content
    color : typing.Optional[typing.Union[int, Color]]
        color code of the embed
    footer : typing.Optional[EmbedFooter]
        footer information
    image : typing.Optional[str]
        image url
    thumbnail : typing.Optional[str]
        thumbnail url
    author : typing.Optional[EmbedAuthor]
        author information
    fields : typing.Optional[list[EmbedField]]
        fields information
    """

    title: typing.Optional[str] = None
    description: typing.Optional[str] = None
    url: typing.Optional[str] = None
    timestamp: typing.Optional[typing.Union[int, datetime]] = None
    color: typing.Optional[typing.Union[int, Color]] = None
    footer: typing.Optional[EmbedFooter] = None
    image: typing.Optional[str] = None
    thumbnail: typing.Optional[str] = None
    author: typing.Optional[EmbedAuthor] = None
    fields: typing.Optional[list[EmbedField]] = None

    def add_field(self, name: str, value: str, inline: bool = False) -> Embed:
        """Adds a field to the embed.

        Parameters
        ----------
        name : str
            name of the field
        value : str
            value of the field
        inline : bool
            whether or not this field should display inline
        """
        if not self.fields:
            self.fields = []

        self.fields.append(EmbedField(name, value, inline))

        return self

    def to_dict(self) -> dict[str, typing.Union[str, int, dict[str, typing.Any]]]:
        """Turns the Embed into a dictionary

        Returns
        -------
        dict[str, typing.Union[str, int, dict[str, typing.Any]]]
            the dictionary made from the attributes
        """
        d = {}

        for k, v in self.__dict__.items():
            if v:
                if k == "timestamp":
                    if isinstance(v, datetime):
                        v = int(v.timestamp())
                    else:
                        v = int(v)
                elif k == "fields":
                    v = [x.to_dict() for x in v]
                elif k == "color":
                    v = int(v)
                elif k in ("image", "thumbnail"):
                    v = {"url": v}

                elif isinstance(v, (EmbedFooter, EmbedAuthor)):
                    v = v.to_dict()

                d[k] = v

        d["type"] = "rich"
        return d

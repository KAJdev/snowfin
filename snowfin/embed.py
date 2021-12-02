from dataclasses import dataclass
from datetime import datetime
from typing import List, Union
from .color import Color

__all__ = (
    'Embed',
    'EmbedAuthor',
    'EmbedField',
    'EmbedFooter'
)

Empty = object()

@dataclass
class EmbedField:
    name: str
    value: str
    inline: bool = False

    def to_dict(self):
        return {
            'name': self.name,
            'value': self.value,
            'inline': self.inline,
        }

@dataclass
class EmbedAuthor:
    name: str
    url: str = Empty
    icon_url: str = Empty

    def to_dict(self):
        d = {
            'name': self.name,
        }
        if self.icon_url is not Empty:
            d['icon_url'] = self.icon_url
        if self.url is not Empty:
            d['url'] = self.url

        return d

@dataclass
class EmbedFooter:
    text: str
    icon_url: str = Empty

    def to_dict(self):
        d = {
            'text': self.text,
        }
        if self.icon_url is not Empty:
            d['icon_url'] = self.icon_url

        return d

@dataclass
class Embed:
    title: str = Empty
    description: str = Empty
    url: str = Empty
    color: Union[int, Color] = Empty
    timestamp: Union[int, datetime] = Empty
    footer: EmbedFooter = Empty
    image: str = Empty
    thumbnail: str = Empty
    author: EmbedAuthor = Empty
    fields: List[EmbedField] = Empty

    def add_field(self, name: str, value: str, inline: bool = False):
        if self.fields is Empty:
            self.fields = []

        self.fields.append(EmbedField(name, value, inline))

        return self

    def to_dict(self):
        d = {}

        for k, v in self.__dict__.items():
            if v is not Empty:
                if k == 'timestamp':
                    if isinstance(v, datetime):
                        v = int(v.timestamp())
                    else:
                        v = int(v)
                elif k == 'fields':
                    v = [x.to_dict() for x in v]
                elif k == 'color':
                    v = int(v)
                elif k in ('image', 'thumbnail'):
                    v = {'url': v}

                elif isinstance(v, (EmbedFooter, EmbedAuthor)):
                    v = v.to_dict()
            
                d[k] = v

        d['type'] = 'rich'
        return d
from dataclasses import asdict
from typing import List, Union
from abc import ABC, abstractmethod

from .embed import Embed
from .interaction import Choice
from .enums import ResponseType
from .components import Components, Button, Select

MISSING = object()

__all__ = (
    'AutocompleteResponse',
    'MessageResponse',
    'DeferredResponse',
    'EditResponse'
)

class _DiscordResponse(ABC):
    def __init__(
        self,
        type: ResponseType,
        **kwargs
    ) -> None:
        self.type = type
        self.data = kwargs

    @abstractmethod
    def to_dict(self):
        return {
            "type": self.type.value,
            "data": self.data
        }

class AutocompleteResponse(_DiscordResponse):
    def __init__(
        self,
        choices: List[Choice],
        **kwargs
    ) -> None:
        super().__init__(ResponseType.AUTOCOMPLETE, choices=choices, **kwargs)

    def to_dict(self):
        return {
            "type": self.type.value,
            "data": {
                "choices": [asdict(x) for x in self.data["choices"]]
            }
        }

class DeferredResponse(_DiscordResponse):
    def __init__(
        self,
        ephemperal: bool = False,
        **kwargs
    ) -> None:

        if ephemperal:
            kwargs['flags'] = 64

        super().__init__(ResponseType.DEFER, **kwargs)

class MessageResponse(_DiscordResponse):
    def __init__(
        self, 
        content: str = MISSING,
        embed: Embed = MISSING,
        embeds: List[Embed] = MISSING,
        components: Components = MISSING,
        ephemeral: bool = False,
        type: ResponseType = ResponseType.SEND_MESSAGE,
    ) -> None:
        self.type = type
        self.content = content
        self.embed = embed
        self.embeds = embeds
        self.components = components
        self.ephemeral = ephemeral

    def add_component(self, component: Union[Button, Select], row: int = None):
        if self.components is MISSING:
            self.components = Components()
        self.components.add_component(component, row)

    def to_dict(self):
        if self.type is ResponseType.PONG:
            return {
                "type": self.type.value,
            }

        data = {}

        if self.embeds is not MISSING:
            data['embeds'] = [e.to_dict() for e in self.embeds]

        if self.embed is not MISSING:
            if 'embeds' not in data:
                data['embeds'] = []
            data['embeds'].append(self.embed.to_dict())

        if self.components is not MISSING:
            data['components'] = self.components.to_dict()

        if self.content is not MISSING:
            data['content'] = self.content

        if self.ephemeral:
            data['flags'] = 64

        return {
            "type": self.type.value,
            "data": data
        }

class EditResponse(MessageResponse):
    def __init__(self, *args, **kwargs) -> None:
        kwargs['type'] = ResponseType.UPDATE_MESSAGE
        if 'ephemeral' in kwargs:
            del kwargs['ephemeral']
        super().__init__(**kwargs)
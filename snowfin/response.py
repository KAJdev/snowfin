from dataclasses import asdict
from typing import Callable, Coroutine, List, Optional, Union, Iterable
from abc import ABC, abstractmethod
import asyncio

from .embed import Embed
from .models import Choice
from .enums import ResponseType
from .components import Components, Button, Select, TextInput

MISSING = object()

__all__ = (
    'AutocompleteResponse',
    'MessageResponse',
    'DeferredResponse',
    'EditResponse',
    'ModalResponse',
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
        *choices: List[Choice],
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
        task: Union[asyncio.Task, Callable] = None,
        ephemeral: bool = False,
        **kwargs
    ) -> None:

        kwargs['flags'] = 64 * int(ephemeral)

        self.task = task

        super().__init__(ResponseType.DEFER, **kwargs)

    def to_dict(self):
        return super().to_dict()

class MessageResponse(_DiscordResponse):
    def __init__(
        self, 
        content: str = MISSING,
        embed: Embed = MISSING,
        embeds: List[Embed] = MISSING,
        components: Components | list[Button | Select] = MISSING,
        ephemeral: bool = False,
        type: ResponseType = ResponseType.SEND_MESSAGE,
    ) -> None:
        self.type = type
        self.content = content
        self.embed = embed
        self.embeds = embeds
        self.ephemeral = ephemeral
        self.components = MISSING

        if components is not MISSING:
            if isinstance(components, list):
                for c in components:
                    self.add_component(c)
            elif isinstance(components, Components):
                self.components = components
            elif isinstance(components, (Button, Select)):
                self.add_component(components)
            else:
                raise TypeError(f"components must be Components or a list of Button and Select, not {components.__class__}")

    def add_component(self, component: Union[Button, Select], row: int = None):
        if isinstance(component, TextInput):
            raise ValueError("TextInput cannot be added to a message")

        if self.components is MISSING:
            self.components = Components()
        self.components.add_component(component, row)

        return self

    def remove_component(self, component: Union[Button, Select, str]):
        if self.components is MISSING:
            self.components = Components()
        self.components.remove_component(component)

        return self

    def add_embed(self, embed: Embed):
        if self.embeds is MISSING:
            self.embeds = []

        if len(self.embeds) >= 10:
            raise ValueError("Cannot add more than 10 embeds to a message")
        self.embeds.append(embed)

        return self

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
        kwargs['type'] = ResponseType.EDIT_ORIGINAL_MESSAGE
        if 'ephemeral' in kwargs:
            del kwargs['ephemeral']
        super().__init__(**kwargs)

    def to_dict(self):
        return super().to_dict()

class ModalResponse(_DiscordResponse):
    def __init__(
        self,
        custom_id: str,
        title: str,
        components: Components | list[TextInput] = MISSING,
    ) -> None:
        self.custom_id = custom_id
        self.title = title
        self.components = MISSING
        
        if components is not MISSING:
            if isinstance(components, list):
                for c in components:
                    self.add_component(c)
            elif isinstance(components, Components):
                self.components = components
            elif isinstance(components, TextInput):
                self.add_component(components)
            else:
                raise TypeError(f"components must be Components or a list of TextInput, not {components.__class__}")

    def add_component(self, component: TextInput, row: int = None):
        if not isinstance(component, TextInput):
            raise ValueError("Modals only support TextInput components")

        if self.components is MISSING:
            self.components = Components()
        self.components.add_component(component, row)

        return self

    def remove_component(self, component: Union[TextInput, str], row: int = None):
        if self.components is MISSING:
            self.components = Components()
        self.components.remove_component(component)

        return self

    def to_dict(self):
        return {
            "type": ResponseType.MODAL.value,
            "data": {
                "custom_id": self.custom_id,
                "title": self.title,
                "components": self.components.to_dict()
            }
        }
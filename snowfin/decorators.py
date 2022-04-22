import asyncio
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Union

from snowfin.enums import ChannelType, CommandType, ComponentType, OptionType
from .models import Choice

__all__ = (
    'SlashCommand',
    'ComponentCallback',
    'ModalCallback',
    'SlashOption',
    'ContextMenu',
    'Listener',
    'slash_command',
    'slash_option',
    'context_menu',
    'message_command',
    'user_command',
    'listen',
    'component_callback',
    'select_callback',
    'button_callback',
    'modal_callback',
)

@dataclass
class Interactable:
    callback: Optional[Callable] = None
    module = None

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    def __str__(self):
        return f'{self.module}:{self.callback.__name__}'

    @property
    def __name__(self) -> str:
        return self.callback.__name__

@dataclass
class FollowupMixin:
    after_callback: Optional[Callable] = None

    def followup(self) -> Callable:
        def wrapper(callback):
            self.after_callback = callback
            return callback

        return wrapper

@dataclass 
class CustomIdMappingsMixin:
    """
    A mixin for converting mappigs within interaction custom ids

    e.g. the custom_id "role:{id}:{user}" provided with the mappings:
    {'id': int, 'user': int} will add the `id` and `user` kwargs with
    converted values if possible.

    example usage:

    ```
    # this will match a custom_id like "add_role:123" and pass the value int(123)
    @button_callback("add_role:{role}")
    async def add_role_via_button(ctx, role: int):
        pass
    ```
    """
    mappings: dict = field(default_factory=dict)
    chopped_id: list[str] = field(default_factory=list)

@dataclass
class InteractionCommand(Interactable, FollowupMixin):
    """
    Discord command
    """
    name: str = None
    default_permission: bool = True

@dataclass
class ComponentCallback(Interactable, FollowupMixin, CustomIdMappingsMixin):
    """
    Discord component callback
    """
    custom_id: str = None
    type: ComponentType = None

@dataclass
class ModalCallback(Interactable, FollowupMixin, CustomIdMappingsMixin):
    """
    Discord modal callback
    """
    custom_id: str = None

@dataclass
class Listener(Interactable):
    """
    Discord listener
    """
    event_name: str = None

@dataclass
class SlashOption:
    """
    Discord command option
    """
    name: str
    type: OptionType
    description: str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[list[Choice]] = None
    options: Optional[list['SlashOption']] = None
    channel_types: Optional[list[ChannelType]] = None
    required: bool = False
    autocomplete: bool = False

    def to_dict(self):
        d = {
            'name': self.name,
            'type': self.type.value if isinstance(self.type, OptionType) else self.type,
            'description': self.description,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'required': self.required,
            'autocomplete': self.autocomplete
        }

        if self.choices:
            d['choices'] = [c.to_dict() if isinstance(c, Choice) else c for c in self.choices]

        if self.options:
            d['options'] = [o.to_dict() if isinstance(o, SlashOption) else o for o in self.options]

        if self.channel_types:
            d['channel_types'] = [c.value if isinstance(c, ChannelType) else c for c in self.channel_types]

        return d

@dataclass
class SlashCommand(InteractionCommand):
    name: str = None
    description: str = "No Description Set"

    options: list[SlashOption | dict] = field(default_factory=list)
    autocomplete_callbacks: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.options:
            self.options = [SlashOption(**o) if isinstance(o, dict) else o for o in self.options]

        if self.callback is not None:
            if hasattr(self.callback, 'options'):
                if not self.options:
                    self.options = []
                self.options += self.callback.options

    def to_dict(self):
        d = {
            'name': self.name,
            'description': self.description,
            'type': CommandType.CHAT_INPUT.value,
            'default_permission': self.default_permission
        }

        if self.options:
            d['options'] = [o.to_dict() if isinstance(o, SlashOption) else o for o in self.options]

        return d

    def autocomplete(self, option_name: str) -> Callable:
        def wrapper(callback):
            self.autocomplete_callbacks[option_name] = callback

            # set the autocomplete value in the corresponding option
            if self.options is None:
                self.options = []
            for option in self.options:
                if option.name == option_name:
                    option.autocomplete = True
                    break
            else:
                raise ValueError(f"Option {option_name} not found")

            return callback

        return wrapper

@dataclass
class ContextMenu(InteractionCommand):
    type: CommandType = None

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type.value,
            'default_permission': self.default_permission
        }

def slash_command(
    name: str,
    description: str = None,
    options: list[SlashOption] = None,
    default_permission: bool = True,
    **kwargs
) -> Callable:
    """
    Create a slash command
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Commands must be coroutines")

        return SlashCommand(
            name=name,
            description=description or callback.__doc__ or "No Description Set",
            options=options or [],
            default_permission=default_permission,
            callback=callback,
            **kwargs
        )
    
    return wrapper

def slash_option(
    name: str,
    description: str,
    type: OptionType,
    min_value: Optional[int | float] = None,
    max_value: Optional[int | float] = None,
    choices: Optional[list[Choice]] = None,
    options: Optional[list[SlashOption]] = None,
    channel_types: Optional[list[ChannelType]] = None,
    required: bool = False,
    autocomplete: bool = False,
) -> Callable:
    """
    Create a slash option
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Commands must be coroutines")

        option = SlashOption(
            name=name,
            description=description,
            type=type,
            min_value=min_value,
            max_value=max_value,
            choices=choices if choices else [],
            options=options,
            channel_types=channel_types,
            required=required,
            autocomplete=autocomplete,
        )

        if not hasattr(callback, 'options'):
            callback.options = []
        callback.options.insert(0, option)

        return callback
    
    return wrapper

def context_menu(
    name: str,
    type: CommandType,
    default_permission: bool = True,
    **kwargs
) -> Callable:
    """
    Create a context menu
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Commands must be coroutines")

        return ContextMenu(
            name=name,
            type=type,
            default_permission=default_permission,
            callback=callback,
            **kwargs
        )
    
    return wrapper

def message_command(
    name: str,
    default_permission: bool = True,
    **kwargs
) -> Callable:
    """
    Create a message command
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Commands must be coroutines")

        return ContextMenu(
            name=name,
            type=CommandType.MESSAGE,
            default_permission=default_permission,
            callback=callback,
            **kwargs
        )
    
    return wrapper

def user_command(
    name: str,
    default_permission: bool = True,
    **kwargs
) -> Callable:
    """
    Create a user command
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Commands must be coroutines")

        return ContextMenu(
            name=name,
            type=CommandType.USER,
            default_permission=default_permission,
            callback=callback,
            **kwargs
        )
    
    return wrapper

def listen(event_name: str = None) -> Callable:
    """
    Create a listener
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Listeners must be coroutines")

        return Listener(
            event_name=event_name or callback.__name__,
            callback=callback
        )
    
    return wrapper

def component_callback(
    custom_id: str,
    type: ComponentType,
    __no_mappings__: bool = False,
    **kwargs
) -> Callable:
    """
    Create a component callback
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callbacks must be coroutines")

        if __no_mappings__:
            mappings = chopped_id = None
        else:
            mappings = kwargs

            chopped_id = []
            left = [custom_id]

            for kw, tp in callback.__annotations__.items():
                if (param := '{'+kw+'}') in custom_id:
                    mappings[kw] = tp
                    _, *left = ''.join(left).split(param)

                    if not _:
                        raise ValueError(f"Mapped custom_id must have characters separating the mapped parameters")

                    chopped_id.append(_)

        return ComponentCallback(
            custom_id=custom_id,
            callback=callback,
            type=type,
            mappings=mappings,
            chopped_id=chopped_id
        )
    
    return wrapper

def select_callback(
    custom_id: str,
    **kwargs
) -> Callable:
    """
    Create a select callback
    """
    return component_callback(custom_id, ComponentType.SELECT, **kwargs)

def button_callback(
    custom_id: str,
    **kwargs
) -> Callable:
    """
    Create a button callback
    """
    return component_callback(custom_id, ComponentType.BUTTON, **kwargs)

def modal_callback(
    custom_id: str,
    __no_mappings__: bool = False,
    **kwargs
) -> Callable:
    """
    Create a modal callback
    """
    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callbacks must be coroutines")

        if __no_mappings__:
            mappings = chopped_id = None
        else:
            mappings = kwargs

            chopped_id = []
            left = [custom_id]

            for kw, tp in callback.__annotations__.items():
                if (param := '{'+kw+'}') in custom_id:
                    mappings[kw] = tp
                    _, *left = ''.join(left).split(param)

                    if not _:
                        raise ValueError(f"Mapped custom_id must have characters separating the mapped parameters")

                    chopped_id.append(_)

        return ModalCallback(
            custom_id=custom_id,
            callback=callback,
            mappings=mappings,
            chopped_id=chopped_id
        )
    
    return wrapper
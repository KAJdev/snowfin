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

    def __call__(self, context, *args, **kwargs):
        return self.callback(context, *args, **kwargs)

@dataclass
class FollowupMixin:
    after_callback: Optional[Callable] = None

    def followup(self) -> Callable:
        def wrapper(callback):
            self.after_callback = callback
            return callback

        return wrapper

@dataclass
class InteractionCommand(Interactable, FollowupMixin):
    """
    Discord command
    """
    name: str = None
    default_permission: bool = True

@dataclass
class ComponentCallback(Interactable, FollowupMixin):
    """
    Discord component callback
    """
    custom_id: str = None
    type: ComponentType = None

@dataclass
class ModalCallback(Interactable, FollowupMixin):
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
            d['choices'] = [c.to_dict() for c in self.choices]

        if self.options:
            d['options'] = [o.to_dict() for o in self.options]

        if self.channel_types:
            d['channel_types'] = [c.value for c in self.channel_types]

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
            d['options'] = [o.to_dict() for o in self.options]

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
        return SlashCommand(
            name=name,
            description=description or callback.__doc__,
            options=options,
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

        if hasattr(callback, 'options'):
            if not callback.options:
                callback.options = []
            callback.options.append(option)

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
        return Listener(
            event_name=event_name or callback.__name__,
            callback=callback
        )
    
    return wrapper

def component_callback(
    custom_id: str,
    type: ComponentType,
    **kwargs
) -> Callable:
    """
    Create a component callback
    """
    def wrapper(callback):
        return ComponentCallback(
            custom_id=custom_id,
            callback=callback,
            type=type,
            **kwargs
        )
    
    return wrapper

def select_callback(
    custom_id: str,
    **kwargs
) -> Callable:
    """
    Create a select callback
    """
    def wrapper(callback):
        return ComponentCallback(
            custom_id=custom_id,
            callback=callback,
            type=ComponentType.SELECT,
            **kwargs
        )
    
    return wrapper

def button_callback(
    custom_id: str,
    **kwargs
) -> Callable:
    """
    Create a button callback
    """
    def wrapper(callback):
        return ComponentCallback(
            custom_id=custom_id,
            callback=callback,
            type=ComponentType.BUTTON,
            **kwargs
        )
    
    return wrapper

def modal_callback(
    custom_id: str,
    **kwargs
) -> Callable:
    """
    Create a modal callback
    """
    def wrapper(callback):
        return ModalCallback(
            custom_id=custom_id,
            callback=callback,
            **kwargs
        )
    
    return wrapper
from contextvars import Context
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Union

from attr import has

from snowfin.enums import ChannelType, CommandType, OptionType
from .models import Choice, Option

__all__ = (
    'SlashCommand',
    'ContextMenu',
    'Listener',
    'slash_command',
    'slash_option',
    'context_menu',
    'message_command',
    'user_command',
    'listen',
)

@dataclass
class InteractionCommand:
    """
    Discord command
    """
    name: str
    callback: Optional[Callable]
    default_permission: bool

    def __call__(self, context, *args, **kwargs):
        return self.callback(context, *args, **kwargs)

@dataclass
class Listener:
    """
    Discord listener
    """
    event_name: str
    callback: Callable

    def __call__(self, context, *args, **kwargs):
        return self.callback(context, *args, **kwargs)

@dataclass
class SlashCommand(InteractionCommand):
    cmd_id = None

    name: str
    description: str = "No Description Set"

    options: list[Option | dict] = field(default_factory=list)
    autocomplete_callbacks: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.options:
            self.options = [Option(**o) if isinstance(o, dict) else o for o in self.options]

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
            for option in self.options:
                if option.name == option_name:
                    option.autocomplete = True
                    break

            return callback

        return wrapper

@dataclass
class ContextMenu(InteractionCommand):
    type: CommandType

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type.value,
            'default_permission': self.default_permission
        }

def slash_command(
    name: str,
    description: str = None,
    options: list[Option] = None,
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
    type: OptionType,
    min_value: Optional[int | float] = None,
    max_value: Optional[int | float] = None,
    choices: Optional[list[Choice]] = None,
    options: Optional[list['Option']] = None,
    channel_types: Optional[list[ChannelType]] = None,
    required: bool = False,
    autocomplete: bool = False,
) -> Callable:
    """
    Create a slash option
    """
    def wrapper(callback):
        if not hasattr(callback, 'cmd_id'):
            raise Exception('Callback must be a SlashCommand')

        option = Option(
            name=name,
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

def listen(event_name: str) -> Callable:
    """
    Create a listener
    """
    def wrapper(callback):
        return Listener(
            event_name=event_name,
            callback=callback
        )
    
    return wrapper
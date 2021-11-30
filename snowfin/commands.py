from typing import Coroutine

from .enums import RequestType, ComponentType, CommandType
from .interaction import Command, Component

__all__ = (
    'InteractionHandler',
)

class InteractionHandler:
    _specific_callbacks = {
        RequestType.APPLICATION_COMMAND: {},
        RequestType.MESSAGE_COMPONENT: {},
        RequestType.APPLICATION_COMMAND_AUTOCOMPLETE: {},
        RequestType.MODAL_SUBMIT: {},
    }

    _generic_callbacks = {
        RequestType.APPLICATION_COMMAND: {
            None: None,
            CommandType.CHAT_INPUT: None,
            CommandType.USER: None,
            CommandType.MESSAGE: None,
        },
        RequestType.MESSAGE_COMPONENT: {
            None: None,
            ComponentType.BUTTON: None,
            ComponentType.SELECT: None,
        },
        RequestType.APPLICATION_COMMAND_AUTOCOMPLETE: None,
        RequestType.MODAL_SUBMIT: None,
    }

    @classmethod
    def register(cls, func: Coroutine, type: RequestType, name: str, **kwargs) -> None:
        if name is None:
            if type is RequestType.MESSAGE_COMPONENT:
                component_type = kwargs.get('component_type', None)

                if component_type not in (ComponentType.BUTTON, ComponentType.SELECT, None):
                    raise ValueError('component type must be BUTTON or SELECT')

                cls._generic_callbacks[type][component_type] = func
            elif type is RequestType.APPLICATION_COMMAND:
                command_type = kwargs.get('command_type', None)

                if command_type not in (CommandType.CHAT_INPUT, CommandType.USER, CommandType.MESSAGE, None):
                    raise ValueError('command type must be CHAT_INPUT, USER, or MESSAGE')

                cls._generic_callbacks[type][command_type] = func
            else:
                cls._generic_callbacks[type] = func

        else:
            cls._specific_callbacks[type][name] = func

    @classmethod
    def get_func(cls, data, type: RequestType) -> Coroutine:
        specific = cls._specific_callbacks[type]
        generic = cls._generic_callbacks[type]
        if isinstance(data, Component):
            return (
                specific.get(data.custom_id, None) or (
                    generic.get(data.component_type, None) or generic.get(None, None)
                )
            )
        elif isinstance(data, Command):
            return (
                specific.get(data.name, None) or (
                    generic.get(data.type, None) or generic.get(None, None)
                )
            )
        else:
            return specific.get(data.name, None) or generic
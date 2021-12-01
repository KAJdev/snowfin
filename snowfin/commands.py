from enum import auto
from typing import Any, Coroutine, get_type_hints

from .enums import RequestType, ComponentType, CommandType
from .interaction import Command, Component

__all__ = (
    'InteractionHandler',
)

class InteractionRoute:
    """
    This class is used to store the data for a route.
    """

    def __init__(
        self,
        callable: Coroutine,
        auto_defer: bool = None,
        defer_after: float = None,
        defer_ephemeral: bool = None
    ) -> None:
        self.routine = callable
        self.auto_defer = auto_defer
        self.defer_after = defer_after
        self.defer_ephemeral = defer_ephemeral

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.routine(*args, **kwargs)

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

    _catch_all_callback = None

    @classmethod
    def register_catch_all(cls, callback: Coroutine) -> None:
        cls._catch_all_callback = InteractionRoute(callback)

    @classmethod
    def register(
        cls,
        func: Coroutine,
        type: RequestType,
        name: str,
        auto_defer: bool = None,
        defer_after: float = None,
        defer_ephemeral: bool = None,
        **kwargs
    ) -> None:
        func = InteractionRoute(func, auto_defer, defer_after, defer_ephemeral)
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

        cb = None
        if isinstance(data, Component):
            cb = (
                specific.get(data.custom_id, None) or (
                    generic.get(data.component_type, None) or generic.get(None, None)
                )
            )
        elif isinstance(data, Command):
            cb = (
                specific.get(data.name, None) or (
                    generic.get(data.type, None) or generic.get(None, None)
                )
            )
        else:
            cb = specific.get(data.name, None) or generic

        if cb is None:
            cb = cls._catch_all_callback

        return cb
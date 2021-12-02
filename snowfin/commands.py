from typing import Any, Coroutine

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
        module: str,
        auto_defer: bool = None,
        defer_after: float = None,
        defer_ephemeral: bool = None
    ) -> None:
        self.routine = callable
        self.module = module
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

    _on_server_start_callbacks = []
    _on_server_stop_callbacks = []

    @classmethod
    def register_catch_all(cls, callback: Coroutine, module: str) -> None:
        cls._catch_all_callback = InteractionRoute(callback, module)

    @classmethod
    def register_on_server_start(cls, callback: Coroutine, module: str) -> None:
        cls._on_server_start_callbacks.append(InteractionRoute(callback, module))

    @classmethod
    def register_on_server_stop(cls, callback: Coroutine, module: str) -> None:
        cls._on_server_stop_callbacks.append(InteractionRoute(callback, module))

    @classmethod
    def register(
        cls,
        func: Coroutine,
        type: RequestType,
        name: str,
        module: str,
        auto_defer: bool = None,
        defer_after: float = None,
        defer_ephemeral: bool = None,
        **kwargs
    ) -> None:
        func = InteractionRoute(func, module, auto_defer, defer_after, defer_ephemeral)
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

    @classmethod
    def remove_module_references(cls, module_name: str):
        to_remove = []
        for type in cls._specific_callbacks:
            for name, func in cls._specific_callbacks[type].items():
                if func.module == module_name:
                    to_remove.append((type, name))

        for type, name in to_remove:
            del cls._specific_callbacks[type][name]

        for type in cls._generic_callbacks:
            if isinstance(cls._generic_callbacks[type], InteractionRoute) and cls._generic_callbacks[type].module == module_name:
                cls._generic_callbacks[type] = None
                break

            if isinstance(cls._generic_callbacks[type], dict):
                for func in cls._generic_callbacks[type].values():
                    if func is not None and func.module == module_name:
                        cls._generic_callbacks[type][func] = None
                        break

        if cls._catch_all_callback is not None and cls._catch_all_callback.module == module_name:
            cls._catch_all_callback = None

        to_remove = []
        for func in cls._on_server_start_callbacks:
            if func.module == module_name:
                to_remove.append(func)

        for func in to_remove:
            cls._on_server_start_callbacks.remove(func)

        to_remove = []
        for func in cls._on_server_stop_callbacks:
            if func.module == module_name:
                to_remove.append(func)
        
        for func in to_remove:
            cls._on_server_stop_callbacks.remove(func)

        
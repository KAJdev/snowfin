import functools
import inspect
from typing import Optional

from .decorators import (
    Interactable,
    InteractionCommand,
    ComponentCallback,
    ModalCallback,
    Listener,
)

__all__ = ("Module",)


class Module:

    auto_defer = (None,)
    description: Optional[str] = (None,)
    enabled: bool = True

    def __new__(cls, client, *args, **kwargs):
        new_cls = super().__new__(cls)

        new_cls.app = client.app
        new_cls.client = client
        new_cls.http = client.http

        new_cls.callbacks = []
        new_cls.description = cls.description or cls.__doc__

        for _name, val in inspect.getmembers(
            new_cls, predicate=lambda x: isinstance(x, Interactable)
        ):
            val.module = new_cls

            if val.callback:
                if not isinstance(val.callback, functools.partial):
                    val_name = val.__name__
                    val.callback = functools.partial(val.callback, new_cls)
                    val.callback.__name__ = val_name

                new_cls.callbacks.append(val)

            if getattr(val, "after_callback", None):
                if not isinstance(val.after_callback, functools.partial):
                    val_name = val.__name__
                    val.after_callback = functools.partial(val.after_callback, new_cls)
                    val.after_callback.__name__ = val_name

            if getattr(val, "autocomplete_callbacks", None):
                for key, ac_callback in val.autocomplete_callbacks.items():
                    if not isinstance(ac_callback, functools.partial):
                        val_name = val.__name__
                        val.autocomplete_callbacks[key] = functools.partial(
                            ac_callback, new_cls
                        )
                        ac_callback.__name__ = val_name

            if isinstance(val, InteractionCommand):
                if not val.parent:
                    client.add_interaction_command(val)
            elif isinstance(val, Listener):
                client.add_listener(val)
            elif isinstance(val, ComponentCallback):
                client.add_component_callback(val)
            elif isinstance(val, ModalCallback):
                client.add_modal_callback(val)

        client.log(f"Loaded {cls.__name__} with {len(new_cls.callbacks)} callbacks")

        return new_cls

    def on_unload(self):
        pass

    def on_load(self):
        pass

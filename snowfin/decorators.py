import asyncio
from dataclasses import dataclass, field, asdict
from functools import partial, partialmethod
import inspect
from typing import Callable, Optional, Union

from snowfin.enums import (
    ChannelType,
    CommandType,
    ComponentType,
    OptionType,
    Permissions,
)
from snowfin.locales import Localization
from .models import Choice, Option

__all__ = (
    "SlashCommand",
    "ComponentCallback",
    "ModalCallback",
    "SlashOption",
    "ContextMenu",
    "Listener",
    "slash_command",
    "slash_option",
    "context_menu",
    "message_command",
    "user_command",
    "listen",
    "component_callback",
    "select_callback",
    "button_callback",
    "modal_callback",
)


@dataclass
class Interactable:
    callback: Optional[Callable] = None
    module = None

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    def __str__(self):
        return f"{self.module}:{self.callback.__name__}"

    @property
    def __name__(self) -> str:
        return self.callback.__name__ if self.callback else None


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
    description: str = "No description set"
    default_member_permissions: Optional[Permissions] = None
    name_localizations: Optional[Localization] = None
    description_localizations: Optional[Localization] = None
    dm_permission: bool = True

    # DEPRECATED
    default_permission: bool = True

    @property
    def resolved_name(self) -> str:
        """
        the resolved name of the command, including the parent group names
        used for callback routing via Client
        """
        return self.name


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
    options: Optional[list["SlashOption"]] = None
    channel_types: Optional[list[ChannelType]] = None
    required: bool = False
    autocomplete: bool = False
    name_localizations: Optional[Localization] = None

    def to_dict(self):
        d = {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, OptionType) else self.type,
            "description": self.description,
            "required": self.required,
        }

        if self.min_value:
            d["min_value"] = self.min_value

        if self.max_value:
            d["max_value"] = self.max_value

        if self.autocomplete:
            d["autocomplete"] = self.autocomplete

        if self.choices:
            d["choices"] = [
                c.to_dict() if isinstance(c, Choice) else c for c in self.choices
            ]

        if self.options:
            d["options"] = [
                o.to_dict() if isinstance(o, SlashOption) else o for o in self.options
            ]

        if self.channel_types:
            d["channel_types"] = [
                c.value if isinstance(c, ChannelType) else c for c in self.channel_types
            ]

        if self.name_localizations:
            d["name_localizations"] = self.name_localizations.to_dict()

        if self.description_localizations:
            d["description_localizations"] = self.description_localizations.to_dict()

        return d


@dataclass
class SlashCommand(InteractionCommand):
    options: list[SlashOption | dict] = field(default_factory=list)
    autocomplete_callbacks: dict = field(default_factory=dict)

    parent: Optional["SlashCommand"] = None

    @property
    def resolved_name(self) -> str:
        """
        the resolved name of the command, including the parent group names
        used for callback routing via Client
        """
        n = self.name

        if self.parent:
            n = f"{self.parent.name} {n}"

            if self.parent.parent:
                n = f"{self.parent.parent.name} {n}"

        return n

    def __post_init__(self):
        if self.options:
            new_options = []

            for option in self.options:
                if isinstance(option, dict):
                    for opt in option.get("options", []):
                        if opt.get("type") in (1, 2):
                            new_options.append(SlashCommand(**opt))
                            continue
                    new_options.append(SlashOption(**option))
                else:
                    new_options.append(option)

            self.options = new_options

        if self.callback is not None:
            if hasattr(self.callback, "options"):
                if not self.options:
                    self.options = []
                self.options += self.callback.options

    @property
    def resolved_type(self) -> int:
        """
        the resolved type of the command, including the parent group types
        used for callback routing via Client
        """
        if self.parent is not None:
            if self.parent.parent is not None:
                return OptionType.SUB_COMMAND.value

            for thing in self.options:
                if isinstance(thing, SlashCommand):
                    return OptionType.SUB_COMMAND_GROUP.value

            return OptionType.SUB_COMMAND.value

        return CommandType.CHAT_INPUT.value

    def get_lowest_command(self, options: list[Option]) -> "SlashCommand":
        """
        get the lowest command in the chain of commands
        """
        for option in options:
            if option.type is OptionType.SUB_COMMAND_GROUP:
                return next(
                    filter(lambda x: x.name == option.name, self.options)
                ).get_lowest_command(option.options)
            elif option.type is OptionType.SUB_COMMAND:
                return (
                    next(filter(lambda x: x.name == option.name, self.options), None),
                    option.options,
                )

        return self, options

    def to_dict(self):
        d = {
            "name": self.name,
            "description": self.description,
            "type": self.resolved_type,
            "options": [],
            "name_localizations": self.name_localizations.to_dict()
            if self.name_localizations
            else None,
            "description_localizations": self.description_localizations.to_dict()
            if self.description_localizations
            else None,
        }

        if not self.parent:
            d.update(
                {
                    "dm_permission": self.dm_permission,
                    "default_permission": self.default_permission,
                    "default_member_permissions": self.default_member_permissions.value
                    if self.default_member_permissions
                    else None,
                }
            )

        if self.options:
            for option in self.options:
                if not isinstance(option, dict):
                    d["options"].append(option.to_dict())

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

    def group(
        self,
        name: str,
        description: str = None,
        default_member_permissions: Permissions = None,
    ) -> "SlashCommand":
        """
        Create a sub command group
        """
        if getattr(self.parent, "parent", None) is not None:
            raise ValueError("Cannot nest command groups deeper than one level")

        group = SlashCommand(
            name=name,
            description=description or "No Description Set",
            default_member_permissions=default_member_permissions,
            parent=self,
        )

        self.options.append(group)

        return group

    def subcommand(
        self,
        name: str,
        description: str = None,
        options: list[SlashOption] = None,
        default_member_permissions: Permissions = None,
        **kwargs,
    ) -> "SlashCommand":
        """
        Create a sub command in the current command group
        """

        def wrapper(callback):
            if not asyncio.iscoroutinefunction(callback):
                raise ValueError("Commands must be coroutines")

            for thing in self.options:
                if (
                    isinstance(thing, SlashCommand)
                    and thing.resolved_type == OptionType.SUB_COMMAND_GROUP.value
                ):
                    raise ValueError(
                        "Cannot mix sub commands and command groups within a single group"
                    )

            cmd = SlashCommand(
                name=name,
                description=description or callback.__doc__ or "No Description Set",
                options=options or [],
                default_member_permissions=default_member_permissions,
                callback=callback,
                parent=self,
                **kwargs,
            )

            self.options.append(cmd)

            return cmd

        return wrapper


@dataclass
class ContextMenu(InteractionCommand):
    type: CommandType = None

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type.value,
            "default_member_permissions": self.default_member_permissions.value
            if self.default_member_permissions
            else None,
            "default_permission": self.default_permission,
            "name_localizations": self.name_localizations.to_dict()
            if self.name_localizations
            else None,
            "description_localizations": self.description_localizations.to_dict()
            if self.description_localizations
            else None,
        }


def slash_command(
    name: str,
    description: str = None,
    options: list[SlashOption] = None,
    default_member_permissions: Optional[Permissions] = None,
    **kwargs,
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
            default_member_permissions=default_member_permissions,
            callback=callback,
            **kwargs,
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

        if not hasattr(callback, "options"):
            callback.options = []
        callback.options.insert(0, option)

        return callback

    return wrapper


def context_menu(
    name: str,
    type: CommandType,
    default_member_permissions: Optional[Permissions] = None,
    **kwargs,
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
            default_member_permissions=default_member_permissions,
            callback=callback,
            **kwargs,
        )

    return wrapper


def message_command(
    name: str, default_member_permissions: Optional[Permissions] = None, **kwargs
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
            default_member_permissions=default_member_permissions,
            callback=callback,
            **kwargs,
        )

    return wrapper


def user_command(
    name: str, default_member_permissions: Optional[Permissions] = None, **kwargs
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
            default_member_permissions=default_member_permissions,
            callback=callback,
            **kwargs,
        )

    return wrapper


def listen(event_name: str = None) -> Callable:
    """
    Create a listener
    """

    def wrapper(callback):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Listeners must be coroutines")

        return Listener(event_name=event_name or callback.__name__, callback=callback)

    return wrapper


def component_callback(
    custom_id: str, type: ComponentType, __no_mappings__: bool = False, **kwargs
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
                if (param := "{" + kw + "}") in custom_id:
                    mappings[kw] = tp
                    _, *left = "".join(left).split(param)

                    if not _:
                        raise ValueError(
                            f"Mapped custom_id must have characters separating the mapped parameters"
                        )

                    chopped_id.append(_)

        return ComponentCallback(
            custom_id=custom_id,
            callback=callback,
            type=type,
            mappings=mappings,
            chopped_id=chopped_id,
        )

    return wrapper


def select_callback(custom_id: str, **kwargs) -> Callable:
    """
    Create a select callback
    """
    return component_callback(custom_id, ComponentType.SELECT, **kwargs)


def button_callback(custom_id: str, **kwargs) -> Callable:
    """
    Create a button callback
    """
    return component_callback(custom_id, ComponentType.BUTTON, **kwargs)


def modal_callback(custom_id: str, __no_mappings__: bool = False, **kwargs) -> Callable:
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
                if (param := "{" + kw + "}") in custom_id:
                    mappings[kw] = tp
                    _, *left = "".join(left).split(param)

                    if not _:
                        raise ValueError(
                            f"Mapped custom_id must have characters separating the mapped parameters"
                        )

                    chopped_id.append(_)

        return ModalCallback(
            custom_id=custom_id,
            callback=callback,
            mappings=mappings,
            chopped_id=chopped_id,
        )

    return wrapper

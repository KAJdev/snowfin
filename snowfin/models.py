from dataclasses import dataclass, field
from lib2to3.pgen2.token import OP
from re import S
from typing import Any, Dict, List, Optional, Union

from .enums import ChannelType, OptionType, CommandType, ComponentType, RequestType
from .embed import Embed

@dataclass
class Choice:
    """
    Class for the choices of an option.
    """
    name: str
    value: Union[str, int, float]

@dataclass
class User:
    id: int
    username: str
    discriminator: str
    avatar: str
    bot: Optional[bool]
    mfa_enabled: Optional[bool]
    banner: Optional[str]
    accent_color: Optional[str]
    locale: Optional[str]
    verified: Optional[bool]
    email: Optional[str]
    flags: Optional[int]
    premium_type: Optional[int]
    public_flags: Optional[int]

@dataclass
class Member:
    user: Optional[User]
    nick: Optional[str]
    avatar: Optional[str]
    roles: list[int]
    joined_at: Optional[str]
    premium_since: Optional[str]
    deaf: bool
    mute: bool
    pending: Optional[bool]
    permissions: Optional[str]
    communication_disabled_until: Optional[str]

@dataclass
class RoleTags:
    bot_id: Optional[int]
    integration_id: Optional[int]
    premium_subscriber: Optional[bool]

@dataclass
class Role:
    id: int
    name: str
    color: int
    hoist: bool
    icon: Optional[str]
    unicode_emoji: Optional[str]
    position: int
    permissions: str
    managed: bool
    mentionable: bool
    tags: Optional[RoleTags]


@dataclass
class Option:
    """
    Discord command option
    """
    name: str
    type: OptionType
    description: str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Choice]] = None
    options: Optional[List['Option']] = None
    channel_types: Optional[List[ChannelType]] = None
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
class Channel:
    id: int
    name: str
    type: ChannelType
    permissions: str
    thread_metadata: Optional[Dict]
    parent_id: Optional[int]

@dataclass
class Component:
    """
    Discord command component
    """
    custom_id: str
    component_type: ComponentType
    values: Optional[List[str]] # for selects
    value: Optional[str] # for inputs

@dataclass
class Message:
    id: int
    channel_id: int
    guild_id: Optional[int]
    author: Optional[User | Member]
    member: Optional[Member]
    content: str
    timestamp: str
    edited_timestamp: Optional[str]
    tts: bool
    mention_everyone: bool
    mentions: list[User]
    mention_roles: list[int]
    attachments: list[dict]
    embeds: list[Embed]
    reactions: list[dict]
    nonce: Optional[str | int]
    pinned: bool
    webhook_id: Optional[int]
    type: int
    activity: Optional[dict]
    application: Optional[dict]
    message_reference: Optional[dict]
    flags: Optional[int]
    referenced_message: Optional['Message']
    interaction: Optional[dict]
    thread: Optional[Channel]
    components: Optional[list[Component]]
    sticker_items: Optional[list[dict]]
    stickers: Optional[list[dict]]

@dataclass
class Resolved:
    users: Optional[Dict[int, User]]
    members: Optional[Dict[int, Member]]
    roles: Optional[Dict[int, Role]]
    channels: Optional[Dict[int, Channel]]
    messages: Optional[Dict[int, Message]]

@dataclass
class Command:
    id: int
    name: str
    guild_id: Optional[int]
    type: CommandType
    resolved: Optional[Resolved]
    options: List[Option] = field(default_factory=list)

@dataclass
class ContextCommand:
    target_id: int
    resolved: Optional[Resolved]

@dataclass
class Interaction:
    id: int
    application_id: int
    type: RequestType
    data: Optional[Union[Command, Component, ContextCommand]]
    guild_id: Optional[int]
    channel_id: Optional[int]
    member: Optional[Member]
    user: Optional[User]
    token: str
    version: int
    message: Optional[Message]

    # added later
    client: Optional[Any]
    author: Optional[dict]
    responded: bool = False

    def __post_init__(self):
        self.author = self.user if self.user else self.member
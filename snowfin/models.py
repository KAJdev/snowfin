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
    permissions: Optional[int]
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
    permissions: int
    managed: bool
    mentionable: bool
    tags: Optional[RoleTags]

@dataclass
class Channel:
    id: int
    name: str
    type: ChannelType
    permissions: int
    thread_metadata: Optional[Dict]
    parent_id: Optional[int]

@dataclass
class Component:
    """
    Discord command component
    """
    custom_id: Optional[str]
    type: ComponentType
    values: Optional[List[str]] # for selects
    value: Optional[str] # for inputs
    components: Optional[List['Component']] # for action rows

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
class Option:
    focused: bool
    name: str
    type: OptionType
    value: Optional[Union[str, int, float]]

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
class ModalSubmit:
    custom_id: str
    components: list[Component]

@dataclass
class Interaction:
    id: int
    application_id: int
    type: RequestType
    data: Optional[Command | Component | ContextCommand | ModalSubmit]
    guild_id: Optional[int]
    channel_id: Optional[int]
    member: Optional[Member]
    user: Optional[User]
    token: str
    version: int
    message: Optional[Message]
    local: Optional[str]
    guild_local: Optional[str]

    # added later
    client: Optional[Any]
    author: Optional[dict]
    responded: bool = False

    def __post_init__(self):
        self.author = self.member if self.member else self.user
from dataclasses import dataclass, field
from datetime import datetime
from dacite import from_dict, config
from typing import Any, Dict, List, Optional, Union

from snowfin.components import Components

from .enums import ChannelType, OptionType, CommandType, ComponentType, Permissions, RequestType
from .embed import Embed

@dataclass
class Choice:
    """
    Class for the choices of an option.
    """
    name: str
    value: Union[str, int, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value
        }

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

    @property
    def avatar_url(self) -> str:
        return f"https://cdn.discordapp.com/avatars/{self.id}/{self.avatar}.png"

@dataclass
class Member:
    user: Optional[User]
    nick: Optional[str]
    avatar: Optional[str]
    roles: list[int]
    joined_at: Optional[str]
    premium_since: Optional[str]
    deaf: Optional[bool]
    mute: Optional[bool]
    pending: Optional[bool]
    permissions: Optional[int]
    communication_disabled_until: Optional[str]

    def __post_init__(self):
        if self.joined_at:
            # get datetime from ISO8601 string
            self.joined_at = datetime.strptime(self.joined_at, '%Y-%m-%dT%H:%M:%S.%f+00:00')

        if self.premium_since:
            # get datetime from ISO8601 string
            self.premium_since = datetime.strptime(self.premium_since, '%Y-%m-%dT%H:%M:%S.%f+00:00')

        if self.communication_disabled_until:
            # get datetime from ISO8601 string
            self.communication_disabled_until = datetime.strptime(self.communication_disabled_until, '%Y-%m-%dT%H:%M:%S.%f+00:00')

    @property
    def avatar_url(self) -> str:
        if self.user is not None:
            return f"https://cdn.discordapp.com/avatars/{self.user.id}/{self.avatar}.png"

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
    component_type: Optional[ComponentType] # for when interaction data
    type: Optional[OptionType] # for when in a message
    values: Optional[List[str]] # for selects
    value: Optional[str] # for inputs
    label: Optional[str] # for inputs
    components: Optional[List['Component']] # for action rows
    style: Optional[int] # for non action rows

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
    mention_roles: list[int]
    mentions: list[User]
    attachments: list[dict]
    embeds: list[Embed]
    reactions: Optional[list[dict]]
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
    components: Optional[list[dict]]
    sticker_items: Optional[list[dict]]
    stickers: Optional[list[dict]]

    def __post_init__(self):
        if self.timestamp:
            # get datetime from ISO8601 string
            self.timestamp = datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S.%f+00:00')

        if self.edited_timestamp:
            # get datetime from ISO8601 string
            self.edited_timestamp = datetime.strptime(self.edited_timestamp, '%Y-%m-%dT%H:%M:%S.%f+00:00')

        if self.components:
            self.components = Components.from_list(self.components)

@dataclass
class Resolved:
    users: Dict[str, User] = field(default_factory=dict)
    members: Dict[str, Member] = field(default_factory=dict)
    roles: Dict[str, Role] = field(default_factory=dict)
    channels: Dict[str, Channel] = field(default_factory=dict)
    messages: Dict[str, Message] = field(default_factory=dict)

    def get(self, type: OptionType, key: str | int) -> Any:
        key = str(key)
        if type is OptionType.USER:
            gotten = self.members.get(key, self.users.get(key))

            if isinstance(gotten, Member):
                gotten.user = self.users.get(key) or gotten.user

            return gotten

        elif type is OptionType.ROLE:
            return self.roles.get(key)
        elif type is OptionType.CHANNEL:
            return self.channels.get(key)
        elif type is OptionType.MENTIONABLE:
            gotten = self.members.get(key, self.users.get(key, self.roles.get(key)))

            if isinstance(gotten, Member):
                gotten.user = self.users.get(key) or gotten.user

            return gotten

@dataclass
class Option:
    focused: Optional[bool]
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
class ModalSubmit:
    custom_id: str
    components: list[Component]

@dataclass
class Interaction:
    id: int
    application_id: int
    type: RequestType
    data: Optional[dict]
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
    responded: bool = False

    def __post_init__(self) -> None:
        _config=config.Config(cast=[
            int,
            ChannelType,
            CommandType,
            OptionType,
            ComponentType,
            RequestType,
            Permissions
        ])

        if self.type in (RequestType.APPLICATION_COMMAND, RequestType.APPLICATION_COMMAND_AUTOCOMPLETE):
            self.data = from_dict(Command, self.data, config=_config)
        elif self.type is RequestType.MESSAGE_COMPONENT:
            self.data = from_dict(Component, self.data, config=_config)
        elif self.type is RequestType.MODAL_SUBMIT:
            self.data = from_dict(ModalSubmit, self.data, config=_config)
        else:
            raise ValueError(f'Unknown request type: {self.type}')

    @property
    def author(self) -> Member | User:
        return self.member if self.member else self.user
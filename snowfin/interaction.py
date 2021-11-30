from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from .enums import ChannelType, OptionType, CommandType, ComponentType, RequestType

@dataclass
class Choice:
    """
    Class for the choices of an option.
    """
    name: str
    value: Union[str, int, float]

@dataclass
class Option:
    """
    Discord command option
    """
    name: str
    type: OptionType
    min_value: Optional[Union[int, float]]
    max_value: Optional[Union[int, float]]
    choices: Optional[List[Choice]]
    options: Optional[List['Option']]
    channel_types: Optional[List[ChannelType]] 
    required: bool = False
    autocomplete: bool = False

@dataclass
class Channel:
    id: int
    name: str
    type: ChannelType
    permissions: str
    thread_metadata: Optional[Dict]
    parent_id: Optional[int]

@dataclass
class Resolved:
    users: Optional[Dict[int, Dict]]
    members: Optional[Dict[int, Dict]]
    roles: Optional[Dict[int, Dict]]
    channels: Optional[Dict[int, Channel]]
    messages: Optional[Dict[int, Dict]]

@dataclass
class Command:
    id: int
    name: str
    guild_id: Optional[int]
    type: CommandType
    resolved: Optional[Resolved]
    options: List[Option] = field(default_factory=list)

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
    member: Optional[Dict]
    user: Optional[Dict]
    token: str
    version: int
    message: Optional[Dict]

    def __post_init__(self):
        self.responded = False

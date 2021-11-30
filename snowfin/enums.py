from enum import Enum

__all__ = (
    'ResponseType',
    'RequestType',
    'ButtonStyle',
    'CommandType',
    'OptionType',
    'ChannelType',
    'ComponentType'
)

class ResponseType(Enum):
    """
    Enum for the different types of responses.
    """
    PONG = 1

    CHANNEL_MESSAGE_WITH_SOURCE = 4
    SEND_MESSAGE = 4

    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFER = 5

    DEFERRED_UPDATE_MESSAGE = 6
    COMPONENT_DEFER = 6

    UPDATE_MESSAGE = 7

    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    AUTOCOMPLETE = 8

class ButtonStyle(Enum):
    """
    Enum for the different button styles.
    """
    PRIMARY = 1
    BLURPLE = 1

    SECONDARY = 2
    GREY = 2
    GRAY = 2

    SECCESS = 3
    GREEN = 3

    DANGER = 4
    RED = 4

    LINK = 5
    URL = 5

class CommandType(Enum):
    """
    Enum for the different types of commands.
    """
    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3

class RequestType(Enum):
    """
    Discord command types
    """
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4

class OptionType(Enum):
    """
    Enum for the different types of options.
    """
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10

class ChannelType(Enum):
    """
    Enum for the different types of channels.
    """
    GUILD_TEXT = 0
    DM = 1
    GUILD_VOICE = 2
    GROUP_DM = 3
    GUILD_CATEGORY = 4
    GUILD_NEWS = 5
    GUILD_STORE = 6
    GUILD_NEWS_THREAD = 10
    GUILD_PUBLIC_THREAD = 11
    GUILD_PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13

class ComponentType(Enum):
    """
    Enum for the different types of components.
    """
    ACTION_ROW = 1
    BUTTON = 2
    SELECT = 3
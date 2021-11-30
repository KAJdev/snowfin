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
    Outgoing response types
    """
    PONG = 1 # shouldn't really ever be used

    CHANNEL_MESSAGE_WITH_SOURCE = 4 # sending an initial message
    SEND_MESSAGE = 4

    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5 # deferring a slash command
    DEFER = 5

    DEFERRED_UPDATE_MESSAGE = 6 # deferring a message component
    COMPONENT_DEFER = 6

    UPDATE_MESSAGE = 7 # editing the original slash command message
    EDIT_ORIGINAL_MESSAGE = 7

    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8 # sending an autocomplete result
    AUTOCOMPLETE = 8

    MODAL = 9 # sending a modal form

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
    CHAT_INPUT = 1 # Slash Command
    USER = 2
    MESSAGE = 3

class RequestType(Enum):
    """
    Incoming discord interaction types
    """
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5

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
    INPUT_TEXT = 4

class TextStyleTypes(Enum):
    SHORT = 1
    PARAGRAPH = 2
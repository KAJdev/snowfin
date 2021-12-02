from typing import Union


class DiscordError(Exception):
    """Base class for all discord errors."""
    pass

class CogLoadError(DiscordError):
    """Raised when a cog cannot be loaded."""
    pass

class HTTPException(DiscordError):

    """Base class for all HTTP-related errors."""

    def __init__(self, message: Union[dict, str]) -> None:
        self.text: str = ''
        if isinstance(message, dict):
            self.text: str = f"{message.get('code', 0)}: {message.get('message', 'Unknown Error')}"
        else:
            self.text: str = message

class Forbidden(HTTPException):
    """Exception raised when a request is forbidden."""
    pass

class NotFound(HTTPException):
    """Exception raised when a resource is not found."""
    pass

class DiscordInternalError(HTTPException):
    """Exception raised when an internal error occurs."""
    pass
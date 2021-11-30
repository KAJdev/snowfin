from typing import Coroutine

from sanic import Sanic, Request
from sanic.response import HTTPResponse, json
from sanic.log import logger

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from dacite import from_dict, config

import snowfin.interaction
from .commands import InteractionHandler
from .response import _DiscordResponse, MessageResponse, EditResponse, DeferredResponse
from .enums import RequestType, ResponseType

__all__ = (
    'SlashCommand',
    'MessageComponent',
    'Autocomplete',
    'Client'
)

def mix_into_commands(func: Coroutine, type: RequestType, name: str = None, **kwargs) -> Coroutine:
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return result

    InteractionHandler.register(wrapper, type, name, **kwargs)
    return wrapper

def SlashCommand(name: str = None) -> Coroutine:
    def decorator(func):
        return mix_into_commands(func, RequestType.APPLICATION_COMMAND, name)
    return decorator

def MessageComponent(custom_id: str = None, type: snowfin.interaction.ComponentType = None) -> Coroutine:
    def decorator(func):
        return mix_into_commands(func, RequestType.MESSAGE_COMPONENT, custom_id, component_type=type)
    return decorator

def Autocomplete(name: str = None) -> Coroutine:
    def decorator(func):
        return mix_into_commands(func, RequestType.APPLICATION_COMMAND_AUTOCOMPLETE, name)
    return decorator


class Client:

    def __init__(self, verify_key: str, app: Sanic = None):
        if app is None:
            self.app = Sanic("snowfin-interactions")
        else:
            self.app = app
        self.verify_key = VerifyKey(bytes.fromhex(verify_key))

        @self.app.on_request
        async def verify_signature(request: Request):
            signature = request.headers["X-Signature-Ed25519"]
            timestamp = request.headers["X-Signature-Timestamp"]
            body = request.body.decode("utf-8")

            try:
                self.verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
            except BadSignatureError:
                return json({"error": "invalid signature"}, status=403)

        @self.app.on_request
        async def parse_request(request: Request):
            request.ctx = from_dict(
                data= request.json,
                data_class=snowfin.interaction.Interaction,
                config=config.Config(
                    cast=[
                        int,
                        snowfin.interaction.ChannelType,
                        snowfin.interaction.CommandType,
                        snowfin.interaction.OptionType,
                        snowfin.interaction.ComponentType,
                        RequestType
                    ]
                )
            )

        @self.app.on_request
        async def ack_request(request: Request):
            if request.ctx.type == RequestType.PING:
                return json({"type": 1})

        @self.app.post("/")
        async def handle_request(request: Request):
            return await self.handle_request(request)

    async def handle_request(self, request: Request) -> HTTPResponse:
        func = InteractionHandler.get_func(request.ctx.data, request.ctx.type)
        if func:
            resp = await func(request)
        else:
            return json({"error": "command not found"}, status=404)

        if isinstance(resp, _DiscordResponse):
            return json(resp.to_dict())
        elif isinstance(resp, HTTPResponse):
            return resp
        else:
            return json({"error": "invalid response type"}, status=500)

    def run(self, host: str, port: int, **kwargs):
        self.app.run(host=host, port=port, **kwargs)
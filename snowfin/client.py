import asyncio
from typing import Coroutine

from sanic import Sanic, Request
from sanic.config import DEFAULT_CONFIG
from sanic.response import HTTPResponse, json
from sanic.log import logger

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from dacite import from_dict, config

import snowfin.interaction
from .commands import InteractionHandler
from .response import _DiscordResponse, DeferredResponse, EditResponse, MessageResponse
from .http import *
from .enums import *

__all__ = (
    'SlashCommand',
    'MessageComponent',
    'Autocomplete',
    'Modal',
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

def Modal(custom_id: str = None) -> Coroutine:
    def decorator(func):
        return mix_into_commands(func, RequestType.MODAL_SUBMIT, custom_id)
    return decorator


class Client:

    def __init__(self, verify_key: str, app: Sanic = None, **kwargs):
        if app is None:
            self.app = Sanic("snowfin-interactions")
        else:
            self.app = app
        self.verify_key = VerifyKey(bytes.fromhex(verify_key))

        self.http: HTTP = HTTP(**dict((x, kwargs.get(x, None)) for x in ('proxy', 'proxy_auth', 'headers')))

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
                        ChannelType,
                        CommandType,
                        OptionType,
                        ComponentType,
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

    def handle_deferred_routine(self, routine: Coroutine, request):
        async def wrapper():
            try:
                response = await routine(request)
                await self.handle_deferred_response(request, response)
            except Exception as e:
                logger.error(e.__repr__())
        task = asyncio.get_event_loop().create_task(wrapper())

    async def handle_deferred_response(self, request, response):
        if response:
            if response.type in (ResponseType.SEND_MESSAGE, ResponseType.EDIT_ORIGINAL_MESSAGE):
                await self.http.edit_original_message(request, response)
            else:
                raise Exception("Invalid response type")

    async def handle_request(self, request: Request) -> HTTPResponse:
        func = InteractionHandler.get_func(request.ctx.data, request.ctx.type)
        if func:
            resp = await func(request)
        else:
            return json({"error": "command not found"}, status=404)

        request.ctx.responded = True

        if isinstance(resp, _DiscordResponse):
            if isinstance(resp, DeferredResponse):
                if request.ctx.type == RequestType.MESSAGE_COMPONENT:
                    resp.type = ResponseType.COMPONENT_DEFER
                else:
                    resp.type = ResponseType.DEFER

                self.handle_deferred_routine(resp.coro, request)
            return json(resp.to_dict())
        elif isinstance(resp, HTTPResponse):
            return resp
        else:
            return json({"error": "invalid response type"}, status=500)

    def run(self, host: str, port: int, **kwargs):
        self.app.run(host=host, port=port, **kwargs)
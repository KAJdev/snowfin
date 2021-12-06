import asyncio
import importlib
from typing import Coroutine

from sanic import Sanic, Request
from sanic.response import HTTPResponse, json
from sanic.log import logger

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from dacite import from_dict, config
from snowfin.errors import CogLoadError

import snowfin.interaction
from .commands import InteractionHandler, InteractionRoute
from .response import _DiscordResponse, DeferredResponse
from .http import *
from .enums import *

__all__ = (
    'slash_command',
    'message_component',
    'autocomplete',
    'modal',
    'anything',
    'on_start',
    'on_stop',
    'before_request',
    'Client'
)

def mix_into_commands(func: Coroutine, type: RequestType, name: str = None, **kwargs) -> Coroutine:
    """
    A global wrapper of a wrapper to add routines to a class object
    """
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return result

    InteractionHandler.register(wrapper, type, name, func.__module__, **kwargs)
    return wrapper

def slash_command(
    name: str = None,
    type: CommandType = None,
    auto_defer: bool = None,
    defer_after: float = None,
    defer_ephemeral: bool = None
) -> Coroutine:
    """
    A decorator for creating slash command callbacks. If name and type are supplied, name is used.
    """
    def decorator(func):
        return mix_into_commands(
            func,
            RequestType.APPLICATION_COMMAND,
            name,
            command_type=type,
            auto_defer=auto_defer,
            defer_after=defer_after,
            defer_ephemeral=defer_ephemeral
        )
    return decorator

def message_component(
    custom_id: str = None,
    type: ComponentType = None,
    auto_defer: bool = None,
    defer_after: float = None,
    defer_ephemeral: bool = None
) -> Coroutine:
    """
    A decorator for creating message component callbacks. If custom_id and type are supplied, custom_id is used.
    """
    def decorator(func):
        return mix_into_commands(
            func, RequestType.MESSAGE_COMPONENT,
            custom_id,
            component_type=type,
            auto_defer=auto_defer,
            defer_after=defer_after,
            defer_ephemeral=defer_ephemeral
        )
    return decorator

def autocomplete(name: str = None) -> Coroutine:
    """
    A decorator for creating autocomplete callbacks.
    """
    def decorator(func):
        return mix_into_commands(func, RequestType.APPLICATION_COMMAND_AUTOCOMPLETE, name)
    return decorator

def modal(custom_id: str = None) -> Coroutine:
    """
    A decorator for creating modal submit callbacks.
    """
    def decorator(func):
        return mix_into_commands(func, RequestType.MODAL_SUBMIT, custom_id)
    return decorator

def anything(func) -> Coroutine:
    """
    A decorator for creating catch all callbacks. Will only call if no other callbacks match.
    """
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return result

    InteractionHandler.register_catch_all(wrapper, func.__module__)
    return wrapper

def on_start(func) -> Coroutine:
    """
    A decorator for creating on_start callbacks. Called when the webserver has started.
    """
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return result

    InteractionHandler.register_on_server_start(wrapper, func.__module__)
    return wrapper

def on_stop(func) -> Coroutine:
    """
    A decorator for creating on_stop callbacks. Called when the webserver is stopping.
    """
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return result

    InteractionHandler.register_on_server_stop(wrapper, func.__module__)
    return wrapper

def before_request(func) -> Coroutine:
    """
    A decorator for creating before_request callbacks. Called before every request regardless of type.
    """
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return result

    InteractionHandler.register_before(wrapper, func.__module__)
    return wrapper


class Client:

    def __init__(self, verify_key: str, app: Sanic = None, auto_defer: bool = False, defer_after: float = 2, defer_ephemeral: bool = False, logging_level: int = 1, **kwargs):
        # create a new app if none is not supplied
        if app is None:
            self.app = Sanic("snowfin-interactions")
        else:
            self.app = app
        self.verify_key = VerifyKey(bytes.fromhex(verify_key))

        # automatic defer options
        self.auto_defer = auto_defer
        self.defer_after = defer_after
        self.defer_ephemeral = defer_ephemeral

        self.log = lambda msg: logger.info(msg)
        self.log_error = lambda msg: logger.error(msg)

        self.http: HTTP = HTTP(**dict((x, kwargs.get(x, None)) for x in ('proxy', 'proxy_auth', 'headers')))

        self.__loaded_cogs = {}

        # create some middleware for start and stop events
        @self.app.listener('after_server_start')
        async def on_start(app, loop):
            await asyncio.gather(*(x(self) for x in InteractionHandler._on_server_start_callbacks))

        @self.app.listener('before_server_stop')
        async def on_stop(app, loop):
            await asyncio.gather(*(x(self) for x in InteractionHandler._on_server_stop_callbacks))

        # create middlware for verifying that discord is the one who sent the interaction
        @self.app.on_request
        async def verify_signature(request: Request):
            signature = request.headers["X-Signature-Ed25519"]
            timestamp = request.headers["X-Signature-Timestamp"]
            body = request.body.decode("utf-8")

            try:
                self.verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
            except BadSignatureError:
                return json({"error": "invalid signature"}, status=403)

        # middlware for constructing dataclasses from json
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

            request.ctx.client = self

        # send PONGs to PINGs
        @self.app.on_request
        async def ack_request(request: Request):
            if request.ctx.type == RequestType.PING:
                return json({"type": 1})

        # handle user callbacks
        @self.app.post("/")
        async def handle_request(request: Request):
            return await self._handle_request(request)

        logger.info("Client initialized")

    @property
    def loop(self):
        return self.app.loop

    def _handle_deferred_routine(self, routine: asyncio.Task, request):
        """
        Create a wrapper for the task supplied and wait on it.
        log any errors and pass the result onward
        """
        async def wrapper():
            try:
                response = await routine
                await self._handle_deferred_response(request, response)
            except Exception as e:
                logger.error(e.__repr__())
        task = asyncio.get_event_loop().create_task(wrapper())

    async def _handle_deferred_response(self, request, response):
        """
        Take the result of a deferred callback task and send a request to the interaction webhook
        """
        if response:
            if response.type in (ResponseType.SEND_MESSAGE, ResponseType.EDIT_ORIGINAL_MESSAGE):
                await self.http.edit_original_message(request, response)
            else:
                raise Exception("Invalid response type")

    async def _handle_request(self, request: Request) -> HTTPResponse:
        """
        Grab the callback Coroutine and create a task.
        """
        # handle the before requests
        await asyncio.gather(*(x(request) for x in InteractionHandler._before_callbacks))

        func: InteractionRoute = InteractionHandler.get_func(request.ctx.data, request.ctx.type)
        if func:
            task = asyncio.create_task(func(request.ctx))

            # auto defer if and only if the decorator and/or client told us too and it *can* be defered
            if (func.auto_defer if func.auto_defer is not None else self.auto_defer) and \
                request.ctx.type in (RequestType.APPLICATION_COMMAND, RequestType.MESSAGE_COMPONENT):
                # we want to defer automatically and keep the original task going
                # so we wait for up to the timeout, then construct a DeferredResponse ourselves
                # then handle_deferred_routine() will do the rest
                done, pending = await asyncio.wait([task], timeout = func.defer_after if func.defer_after is not None else self.defer_after)


                if task in pending:
                    # task didn't return in time, let it keep going and construct a defer for it
                    resp = DeferredResponse(task,
                        ephemeral=func.defer_ephemeral if func.defer_ephemeral is not None else self.defer_ephemeral
                    )
                else:
                    # the task returned in time, get the result and use that like normal
                    resp = task.result()
            else:
                resp = await task
        else:
            return json({"error": "command not found"}, status=404)

        if request.ctx.responded:
            raise Exception("Callback already responded")

        if not isinstance(resp, DeferredResponse):
            request.ctx.responded = True

        if isinstance(resp, _DiscordResponse):
            if isinstance(resp, DeferredResponse):
                # make sure we are sending the correct interaction response type for the request
                if request.ctx.type == RequestType.MESSAGE_COMPONENT:
                    resp.type = ResponseType.COMPONENT_DEFER
                else:
                    resp.type = ResponseType.DEFER

                # if someone passed in a callable, construct a task for them to keep syntax as clean as possible
                if not isinstance(resp.task, asyncio.Task):
                    resp.task = asyncio.create_task(resp.task(request.ctx))

                # start or continue the task and post the response to a webhook
                self._handle_deferred_routine(resp.task, request)
            
            # do some logging and return the 'dictified' data
            data = resp.to_dict()
            if self.app.debug: self.log(data)
            return json(data)

        elif isinstance(resp, HTTPResponse):
            # someone gave us a sanic response, Assume they know what they are doing
            return resp
            
        else:
            return json({"error": "invalid response type"}, status=500)

    def run(self, host: str, port: int, **kwargs):
        self.app.run(host=host, port=port, access_log=False, **kwargs)

    def add_cog(self, module_name: str):
        resolved_name = importlib.util.resolve_name(module_name, __spec__.parent)

        if resolved_name in self.__loaded_cogs:
            raise CogLoadError(f"{module_name} already loaded")

        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            raise CogLoadError(f"{module_name} failed to load: {e}")
        self.__loaded_cogs[resolved_name] = module
        if hasattr(module, "setup"):
            module.setup(self)

    def remove_cog(self, module: str):
        module_name = importlib.util.resolve_name(module, __spec__.parent)
        
        if module_name not in self.__loaded_cogs:
            raise ValueError(f"{module_name} not loaded")

        module_ = self.__loaded_cogs.pop(module_name)

        InteractionHandler.remove_module_references(module_name)
        if hasattr(module_, "teardown"):
            module_.teardown(self)

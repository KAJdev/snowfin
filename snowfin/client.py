import asyncio
from contextvars import Context
from dataclasses import dataclass
import importlib
import inspect
import sys
from typing import Callable, Coroutine, Optional

from sanic import Sanic, Request
import sanic
from sanic.response import HTTPResponse, json
from sanic.log import logger

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from dacite import from_dict, config
from snowfin.errors import CogLoadError

import snowfin.interaction
from .decorators import InteractionCommand
from .response import _DiscordResponse, DeferredResponse
from .http import *
from .decorators import *
from .enums import *

__all__ = (
    'Client',
    'AutoDefer',
)

@dataclass
class AutoDefer:
    enabled: bool = False
    timeout: int = 1
    ephemeral: bool = False

class Client:

    def __init__(self, verify_key: str, application_id: int, sync_commands: bool = False, token: str = None, auto_defer: AutoDefer | bool = AutoDefer(), app: Sanic = None, logging_level: int = 1, **kwargs):
        # create a new app if none is not supplied
        if app is None:
            self.app = Sanic("snowfin-interactions")
        else:
            self.app = app
        self.verify_key = VerifyKey(bytes.fromhex(verify_key))

        # automatic defer options
        self.auto_defer = auto_defer or AutoDefer()

        if self.auto_defer is True:
            self.auto_defer = AutoDefer(enabled=True)

        self.sync_commands = sync_commands

        self.log = lambda msg: logger.info(msg)
        self.log_error = lambda msg: logger.error(msg)

        self.http: HTTP = HTTP(
            application_id=application_id,
            token=token,
            proxy=kwargs.get('proxy', None),
            proxy_auth=kwargs.get('proxy_auth', None),
            headers=kwargs.get('headers', None),
        )

        self.__loaded_cogs = {}

        # listeners for events
        self._listeners: dict[str, list] = {}

        # commands
        self.commands: list[InteractionCommand] = []

        # gather callbacks
        self._gather_callbacks()

        # create some middleware for start and stop events
        @self.app.listener('after_server_start')
        async def on_start(app, loop):
            if self.sync_commands:

                type_classes = {
                    CommandType.CHAT_INPUT.value: SlashCommand,
                    CommandType.MESSAGE.value: ContextMenu,
                    CommandType.USER.value: ContextMenu
                }

                current_commands = [
                    from_dict(data=cmd, data_class=type_classes.get(cmd.get('type')))
                    for cmd in await self.http.get_global_application_commands()
                ]

                if [x.to_dict() for x in current_commands] != [x.to_dict() for x in self.commands]:
                    self.log(f"syncing {len(self.commands)} commands")
                    await self.http.bulk_overwrite_global_application_commands(
                        [command.to_dict() for command in self.commands]
                    )
                    self.log(f"synced {len(self.commands)} commands")

            self.dispatch('start')

        @self.app.listener('before_server_stop')
        async def on_stop(app, loop):
            self.dispatch('stop')

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
        try:
            return self.app.loop
        except sanic.exceptions.SanicException:
            return None

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
        asyncio.create_task(wrapper())

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
        self.dispatch('before_request', request.ctx)

        func: Optional[Callable] = None

        if request.ctx.type is RequestType.APPLICATION_COMMAND:
            cmd: SlashCommand = self.get_command(request.ctx.data.name)
            if cmd:
                func = cmd.callback
        elif request.ctx.type is RequestType.APPLICATION_COMMAND_AUTOCOMPLETE:
            cmd: SlashCommand = self.get_command(request.ctx.data.command.name)
            if cmd:
                selected_option = None

                for option in request.ctx.data.options:
                    if option.focused:
                        selected_option = option
                        break

                func = cmd.autocomplete_callbacks.get(selected_option.name) if selected_option else None
        elif request.ctx.type is RequestType.MESSAGE_COMPONENT:
            pass
        elif request.ctx.type is RequestType.MODAL_SUBMIT:
            pass

        if func:
            task = asyncio.create_task(func(self, request.ctx))

            # auto defer if and only if the decorator and/or client told us too and it *can* be defered
            if self.auto_defer.enabled and \
                request.ctx.type in (RequestType.APPLICATION_COMMAND, RequestType.MESSAGE_COMPONENT):
                # we want to defer automatically and keep the original task going
                # so we wait for up to the timeout, then construct a DeferredResponse ourselves
                # then handle_deferred_routine() will do the rest
                done, pending = await asyncio.wait([task], timeout = self.auto_defer.timeout)


                if task in pending:
                    # task didn't return in time, let it keep going and construct a defer for it
                    resp = DeferredResponse(task,
                        ephemeral=self.auto_defer.ephemeral
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
                    resp.task = asyncio.create_task(resp.task(self, request.ctx))

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

        if hasattr(module_, "teardown"):
            module_.teardown(self)

    def _gather_callbacks(self) -> None:
        """
        Gather all callbacks from loaded modules
        """

        def process(_cmds) -> None:

            for func in _cmds:
                if isinstance(func, InteractionCommand):
                    self.add_interaction_command(func)
                elif isinstance(func, Listener):
                    self.add_listener(func)

            self.log(f"Loaded {len(_cmds)} callbacks")

        process(
            [obj for _, obj in inspect.getmembers(sys.modules["__main__"]) + inspect.getmembers(self) if isinstance(obj, (InteractionCommand, Listener))]
        )

    def add_interaction_command(self, command: InteractionCommand):
        """
        Add a command to the client
        """
        if command.name in [x.name for x in self.commands]:
            raise ValueError(f"/{command.name} already exists")

        self.commands.append(command)

    def add_listener(self, listener: Listener):
        """
        Add a listener to the client
        """
        if listener in self._listeners.get(listener.event_name, []):
            raise ValueError(f"{listener} already exists")

        self._listeners.setdefault(listener.event_name, []).append(listener)

    def dispatch(self, event: str, *args, **kwargs) -> None:
        """
        Dispatch an event to all listeners
        """
        for listener in self._listeners.get(event, []):
            asyncio.create_task(
                listener(*args, **kwargs),
                name=f"snowfin:: {event}"
            )

    def get_command(self, name: str) -> InteractionCommand:
        """
        Get a command by name
        """
        for command in self.commands:
            if command.name == name:
                return command

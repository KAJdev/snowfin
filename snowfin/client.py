import asyncio
from contextlib import suppress
from dataclasses import dataclass
import functools
import importlib
import inspect
import sys
from typing import Callable, Optional
from functools import partial

from sanic import Sanic, Request
import sanic
from sanic.response import HTTPResponse, json
from sanic.log import logger

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from dacite import from_dict, config
from snowfin.components import Components, TextInput, is_component
from snowfin.errors import CogLoadError

from snowfin.models import *
from snowfin.module import Module
from .decorators import Interactable, InteractionCommand
from .response import _DiscordResponse, AutocompleteResponse, DeferredResponse, MessageResponse, ModalResponse
from .http import *
from .decorators import *
from .enums import *

from json import dumps

__all__ = (
    'Client',
    'AutoDefer',
)

cast_config=config.Config(
    cast=[
        int,
        ChannelType,
        CommandType,
        OptionType,
        ComponentType,
        RequestType
    ]
)

@dataclass
class AutoDefer:
    enabled: bool = False
    timeout: int = 1
    ephemeral: bool = False

class Client:

    def __init__(
        self,
        verify_key: str,
        application_id: int,
        sync_commands: bool = False,
        token: str = None,
        auto_defer: AutoDefer | bool = AutoDefer(),
        app: Sanic = None,
        logging_level: int = 1,
        **kwargs
    ):
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

        self.log = lambda *msgs: logger.info(' '.join(str(msg) for msg in msgs))
        self.error = lambda *msgs: logger.error(' '.join(str(msg) for msg in msgs))

        self.http: HTTP = HTTP(
            application_id=application_id,
            token=token,
            proxy=kwargs.get('proxy', None),
            proxy_auth=kwargs.get('proxy_auth', None),
            headers=kwargs.get('headers', None),
        )

        self.user: User = None

        self.modules = {}

        # listeners for events (read only events)
        self._listeners: dict[str, list] = {}

        # strict callbacks (returns a response)
        self.commands: list[InteractionCommand] = []
        self.modals: dict[str, ModalCallback] = {}
        self.components: dict[tuple[str, ComponentType], ComponentCallback] = {}

        # gather callbacks
        self._gather_callbacks()

        # create some middleware for start and stop events
        @self.app.listener('after_server_start')
        async def on_start(app, loop):
            await self._sync_commands()
            self.dispatch('start')

            if self.http.application_id:
                self.user = await self.fetch_user(self.http.application_id)

        @self.app.listener('before_server_stop')
        async def on_stop(app, loop):
            self.dispatch('stop')

        # create middlware for verifying that discord is the one who sent the interaction
        @self.app.on_request
        async def verify_signature(request: Request):
            signature = request.headers.get("X-Signature-Ed25519")
            timestamp = request.headers.get("X-Signature-Timestamp")
            body = request.body.decode("utf-8")

            try:
                self.verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
            except BadSignatureError:
                return json({"error": "invalid signature"}, status=403)

        # send PONGs to PINGs and construct the interaction context
        @self.app.on_request
        async def ack_request(request: Request):
            if request.json.get('type') == RequestType.PING.value:
                return json({"type": 1})

            # if self.app.debug:
            #     self.log(f"{request.method} {request.path}\n\n{dumps(request.json, indent=2)}")

            request.ctx = from_dict(
                data= request.json,
                data_class=Interaction,
                config=cast_config
            )

            request.ctx.client = self

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
    
    async def _sync_commands(self):
        if self.sync_commands:
            type_classes = {
                CommandType.CHAT_INPUT.value: SlashCommand,
                CommandType.MESSAGE.value: ContextMenu,
                CommandType.USER.value: ContextMenu
            }

            current_commands = [
                from_dict(data=cmd, data_class=type_classes.get(cmd.get('type')), config=cast_config)
                for cmd in await self.http.get_global_application_commands()
            ]

            current_commands = [x.to_dict() for x in current_commands]
            gathered_commands = [x.to_dict() for x in self.commands]

            for cmd in gathered_commands:
                if cmd not in current_commands:
                    
                    self.log(f"syncing {len(self.commands)} commands")
                    await self.http.bulk_overwrite_global_application_commands(gathered_commands)
                    self.log(f"synced {len(self.commands)} commands")

                    return
                

    def _handle_deferred_routine(self, routine: asyncio.Task, request, after: Optional[Callable]):
        """
        Create a wrapper for the task supplied and wait on it.
        log any errors and pass the result onward
        """
        async def wrapper():
            try:
                response = await routine
                await self._handle_deferred_response(request, response)

                # call the after callback if it exists
                if after:
                    await self._handle_followup_response(request, after)
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

    async def _handle_followup_response(self, request, after):
        """
        Take the result of a followup and send a request to the interaction webhook
        """
        response = await after()

        if response:
            if not isinstance(response, (_DiscordResponse, HTTPResponse)):
                response = self.infer_response(response)

            if response.type is ResponseType.SEND_MESSAGE:
                await self.http.send_followup(request, response)
            elif response.type is ResponseType.EDIT_ORIGINAL_MESSAGE:
                await self.http.edit_original_message(request, response)
            else:
                raise Exception("Invalid response type")

    def infer_response(self, resp: Any) -> _DiscordResponse:
        kwargs = {}
        chosen_type = None

        if not isinstance(resp, tuple):
            resp = [resp]
            
        for arg in resp:
            if isinstance(arg, ResponseType):
                kwargs['type'] = arg

            elif isinstance(arg, Embed):
                kwargs.setdefault('embeds', []).append(arg)
                chosen_type = chosen_type or MessageResponse

            elif is_component(arg):
                kwargs.setdefault('components', Components()).add_component(arg)
                chosen_type = chosen_type or (ModalResponse if isinstance(arg, TextInput) else MessageResponse)

            elif isinstance(arg, Components):
                kwargs['components'] = arg

                for row in arg.rows:
                    for component in row.components:
                        if isinstance(component, TextInput):
                            chosen_type = chosen_type or ModalResponse
                            break
                else:
                    chosen_type = chosen_type or MessageResponse

            elif isinstance(arg, str):
                kwargs['content'] = arg
                chosen_type = chosen_type or MessageResponse

            elif isinstance(arg, list):
                kwargs.setdefault('choices', []).extend(arg)
                chosen_type = chosen_type or AutocompleteResponse

            elif isinstance(arg, dict):
                kwargs.update(arg)
            else:
                raise ValueError(f"Invalid response type {arg}")

        return (chosen_type or MessageResponse)(**kwargs)

    async def _handle_request(self, request: Request) -> HTTPResponse:
        """
        Grab the callback Coroutine and create a task.
        """
        # handle the before requests
        self.dispatch('before_request', request.ctx)

        func: Optional[Callable] = None
        after: Optional[Callable] = None

        if request.ctx.type is RequestType.APPLICATION_COMMAND:
            self.dispatch('command', request.ctx)

            if cmd := self.get_command(request.ctx.data.name):
                kwargs = {}

                for option in request.ctx.data.options:

                    converted = option.value
                    if option.type in (OptionType.CHANNEL, OptionType.USER, OptionType.ROLE, OptionType.MENTIONABLE):
                        converted = request.ctx.data.resolved.get(option.type, option.value)
                    else:
                        converted = type(option.value)

                    kwargs[option.name] = converted
                        

                func = partial(cmd.callback, request.ctx, **kwargs)
                if cmd.after_callback:
                    after = partial(cmd.after_callback, request.ctx, **kwargs)

        elif request.ctx.type is RequestType.APPLICATION_COMMAND_AUTOCOMPLETE:
            self.dispatch('autocomplete', request.ctx)

            if cmd := self.get_command(request.ctx.data.name):
                for option in request.ctx.data.options:
                    if option.focused:
                        callback = cmd.autocomplete_callbacks.get(option.name)
                        if callback:
                            func = partial(callback, request.ctx, option.value)
                        break

        elif request.ctx.type is RequestType.MESSAGE_COMPONENT:
            self.dispatch('component', request.ctx)

            func, after = self.package_component_callback(
                request.ctx.data.custom_id,
                request.ctx.data.component_type,
                request.ctx
            )

        elif request.ctx.type is RequestType.MODAL_SUBMIT:
            self.dispatch('modal', request.ctx)

            if modal := self.modals.get(request.ctx.data.custom_id):
                func = partial(modal, request.ctx)

                if modal.after_callback:
                    after = partial(modal.after_callback, request.ctx)

        if self.app.debug: self.log(f"getting callback for {request.ctx.type}: found", f"{func.func.__name__}{func.args[1:]}" if func else None)

        if func:
            task = asyncio.create_task(func())

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

        if not isinstance(resp, (_DiscordResponse, HTTPResponse)):
            resp = self.infer_response(resp)

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
                self._handle_deferred_routine(resp.task, request, after)
            else:
                # launch after callbacks if there is any and the command is not a deferred one
                if after:
                    asyncio.create_task(self._handle_followup_response(request, after))
            
            # do some logging and return the 'dictified' data
            data = resp.to_dict()
            if self.app.debug: self.log(f"RESPONDING {request.ctx.type} `{getattr(request.ctx.data, 'name', None)}`", data)
            return json(data)

        elif isinstance(resp, HTTPResponse):
            # someone gave us a sanic response, Assume they know what they are doing
            return resp


    def run(self, host: str, port: int, **kwargs):
        self.app.run(host=host, port=port, access_log=False, **kwargs)

    def load_module(self, module_name: str):
        resolved_name = importlib.util.resolve_name(module_name, __spec__.parent)

        if resolved_name in self.modules:
            raise CogLoadError(f"{module_name} already loaded")

        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            raise CogLoadError(f"{module_name} failed to load: {e}")
        self.modules[resolved_name] = []
        
        # go through every class that inherits from Module
        for cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls[1], Module) and cls[1].enabled and cls[1] != Module:
                new_module = cls[1](self)
                self.modules[resolved_name].append(new_module)

                if hasattr(new_module, 'on_load'):
                    new_module.on_load()
                
    def unload_module(self, module: str):
        module_name = importlib.util.resolve_name(module, __spec__.parent)
        
        if module_name not in self.modules:
            raise ValueError(f"{module_name} not loaded")

        modules: list[Module] = self.modules.pop(module_name)

        for module in modules:
            if hasattr(module, "on_unload"):
                module.on_unload()

            # unload all callbacks
            for callback in module.callbacks:
                self.remove_callback(callback)

            del module

    def get_module(self, name: str) -> Optional[Module]:
        """
        Get a loaded module by name
        """

        for modules in self.modules.values():
            for module in modules:
                if module.__class__.__name__ == name:
                    return module

    def _ingest_callbacks(self, *callbacks: Interactable):
        for func in callbacks:
            if isinstance(func, InteractionCommand):
                self.add_interaction_command(func)
            elif isinstance(func, Listener):
                self.add_listener(func)
            elif isinstance(func, ComponentCallback):
                self.add_component_callback(func)
            elif isinstance(func, ModalCallback):
                self.add_modal_callback(func)

    def _gather_callbacks(self) -> None:
        """
        Gather all callbacks from loaded modules
        """
        callbacks = [obj for _, obj in inspect.getmembers(sys.modules["__main__"]) + inspect.getmembers(self) if isinstance(obj, Interactable)]
        self._ingest_callbacks(*callbacks)
        self.log(f"Gathered {len(callbacks)} immediate callbacks")

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
        listener.event_name = listener.event_name.removeprefix("on_")

        if listener in self._listeners.get(listener.event_name, []):
            raise ValueError(f"{listener} already exists")

        self._listeners.setdefault(listener.event_name, []).append(listener)

    def add_component_callback(self, callback: ComponentCallback):
        """
        Add a component callback to the client
        """
        if (callback.custom_id, callback.type) in self.components:
            raise ValueError(f"{callback.type} with custom_id `{callback.custom_id}` already exists")

        self.components[(callback.custom_id, callback.type)] = callback

    def add_modal_callback(self, callback: ModalCallback):
        """
        Add a modal callback to the client
        """
        if callback.custom_id in self.modals:
            raise ValueError(f"modal with custom_id `{callback.custom_id}` already exists")

        self.modals[callback.custom_id] = callback

    def dispatch(self, event: str, *args, **kwargs) -> None:
        """
        Dispatch an event to all listeners
        """
        self.log(f"Dispatching {event}")
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

    def package_component_callback(self, custom_id: str, component_type: ComponentType, ctx: Interaction) -> Callable:
         # loop through all all our registered component callbacks
        for (_id, _type), callback in self.components.items():

            # check the type first and foremost
            if _type == component_type:

                kwargs = {}

                # make sure there are actually mappings to check
                if None not in (callback.mappings, callback.chopped_id):
                    just_values = []

                    left = custom_id

                    # go through all the constants in the defined custom_id and
                    # check if they match the mappings. Construct a list of the
                    # values to pass to the callback and convert
                    for i in range(len(callback.chopped_id)):
                        
                        # this is the next constant in the custom_id
                        segment = callback.chopped_id[i]

                        # make sure the constant is in the custom_id
                        if segment not in left:
                            break

                        # strip the constant from the custom_id so we know that
                        # the next part of the string is the value
                        left = left.removeprefix(segment)
                        if i+1 < len(callback.mappings):
                            value = left.strip(callback.chopped_id[i+1])[0]
                        else:
                            value = left
                        
                        just_values.append(value)

                        # remove the value from the custom_id so we know
                        # that the next part of the string is the next constant
                        left = left.removeprefix(value)
                            
                    # check to make sure that we have the right number of values collected
                    if len(just_values) != len(callback.mappings):
                        continue

                    mappings = callback.mappings.items()
                    for i, (name, _type) in enumerate(mappings):
                        # convert the value to the correct type if possible

                        kwargs[name] = just_values[i]

                        with suppress(ValueError):
                            kwargs[name] = _type(kwargs[name])
                elif _id != custom_id:
                        continue


                return (
                    functools.partial(callback.callback, ctx, **kwargs),
                    functools.partial(callback.after_callback, ctx, **kwargs) if callback.after_callback else None
                )

        return None, None


    def remove_callback(self, callback: Interactable):
        """
        Remove a callback from the client
        """
        if isinstance(callback, InteractionCommand):
            self.commands.remove(callback)
        elif isinstance(callback, Listener):
            self._listeners.get(callback.event_name, []).remove(callback)
        elif isinstance(callback, ComponentCallback):
            self.components.pop((callback.custom_id, callback.type))
        elif isinstance(callback, ModalCallback):
            self.modals.pop(callback.custom_id)



    async def fetch_user(self, user_id: int) -> User:
        """
        Fetch a user object
        """
        data = await self.http.fetch_user(user_id)
        if data is not None:
            return from_dict(User, data, config=cast_config)
from email.mime import application
from typing import Any, Optional
import aiohttp
import json
import sanic
from dataclasses import asdict
from snowfin.decorators import SlashOption

from snowfin.response import _DiscordResponse
from snowfin.enums import CommandType

from .errors import *

__all__ = (
    'HTTP',
    'Route'
)

class Route:
    BASE: str = "https://discord.com/api/v10"

    def __init__(self, method: str, path: str, auth: bool = False, **params) -> None:
        self.method: str = method
        self.path: str = path
        self.url: str = self.BASE + self.path
        self.auth = auth
        self.params: dict = params

    def format(self, **extra_params) -> None:
        self.params.update(extra_params)
        for param,value in self.params.items():
            self.url = self.url.replace('{'+param+'}', str(value))

class HTTP:
    """
    HTTP class
    """
    def __init__(
        self,
        application_id: int,
        token: Optional[str] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[aiohttp.BasicAuth] = None,
        headers: Optional[dict] = None,
    ) -> None:
        self.application_id = application_id
        self.token = token
        self.proxy: Optional[str] = proxy
        self.proxy_auth: Optional[aiohttp.BasicAuth] = proxy_auth
        self.headers: dict = {
            "User-Agent": "Snowfin (https://github.com/kajdev/snowfin)",
        }

        if headers is not None:
            self.headers.update(headers)

    async def request(
        self,
        route: Route,
        data: Optional[dict] = None,
        **kwargs
    ) -> Any:
        """
        Make a followup request
        """
        print(f"Requesting {route.method} {route.url} with {data}")

        headers = self.headers.copy()

        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        if route.auth:
            if self.token is None:
                raise Exception(
                    "You must provide a token to make an authenticated request"
                )

            headers['Authorization'] = f"Bot {self.token}"

        route.format(application_id=self.application_id)

        async with aiohttp.ClientSession() as session:
            async with session.request(
                route.method,
                route.url,
                headers=headers,
                proxy=self.proxy,
                proxy_auth=self.proxy_auth,
                json=data if data is not None else None
            ) as response:

                response_data = None
                text = await response.text(encoding='utf-8')
                try:
                    if response.headers['content-type'] == 'application/json':
                        response_data = json.loads(text)
                except KeyError:
                    pass

                if 300 > response.status >= 200:
                    return response_data

                if response.status == 403:
                    raise Forbidden(response_data)
                elif response.status == 404:
                    raise NotFound(response_data)
                elif response.status >= 500:
                    raise DiscordInternalError(response_data)
                else:
                    print(f"Unknown error: {response.status}")
                    raise HTTPException(response_data)

    async def close(self) -> None:
        """
        Close the HTTP session
        """
        await self._session.close()
    
    def send_followup(
        self,
        request: sanic.Request,
        response: _DiscordResponse,
        **kwargs
    ) -> Any:
        """
        Send a message
        """
        r = Route('POST', '/webhooks/{application_id}/{interaction_token}',
            interaction_token = request.ctx.token
        )

        return self.request(r,
            data=response.to_dict().get('data', {}),
            **kwargs
        )

    def edit_original_message(
        self,
        request: sanic.Request,
        response: _DiscordResponse,
        **kwargs
    ) -> Any:
        """
        Edit the original message
        """
        r = Route('PATCH', '/webhooks/{application_id}/{interaction_token}/messages/@original',
            interaction_token = request.ctx.token
        )

        data = response.to_dict().get('data', {})
        print(data)

        return self.request(r,
            data=data,
            **kwargs
        )

    def delete_original_message(
        self,
        request: sanic.Request,
        **kwargs
    ) -> Any:
        """
        Delete the original message
        """
        r = Route('DELETE', '/webhooks/{application_id}/{interaction_token}/messages/@original',
            interaction_token = request.ctx.token
        )

        return self.request(r, **kwargs)

    def edit_followup_message(
        self,
        request: sanic.Request,
        response: _DiscordResponse,
        message: int,
        **kwargs
    ) -> Any:
        """
        Edit the followup message
        """
        r = Route('PATCH', '/webhooks/{application_id}/{interaction_token}/messages/{message_id}',
            interaction_token = request.ctx.token,
            message_id = message
        )

        return self.request(r,
            data=response.to_dict().get('data', {}),
            **kwargs
        )

    def get_global_application_commands(
        self,
        **kwargs
    ) -> Any:
        """
        Get global application commands
        """
        r = Route('GET', '/applications/{application_id}/commands',
            auth=True
        )

        return self.request(r, **kwargs)

    def create_global_application_command(
        self,
        name: str,
        description: str,
        type: CommandType,
        name_localizations: Optional[dict] = None,
        description_localizations: Optional[dict] = None,
        options: Optional[list[Union[dict, SlashOption]]] = None,
        default_permission: bool = True,
        **kwargs
    ) -> Any:
        """
        Create global application command
        """
        r = Route('POST', '/applications/{application_id}/commands',
            auth=True
        )

        return self.request(r, 
            data={
                "name": name,
                "description": description,
                "type": type.value,
                "name_localizations": name_localizations,
                "description_localizations": description_localizations,
                "options": [asdict(o) if isinstance(o, SlashOption) else o for o in options],
                "default_permission": default_permission
            }
            **kwargs
        )

    def get_global_application_command(
        self,
        command_id: int,
        **kwargs
    ) -> Any:
        """
        Get global application command
        """
        r = Route('GET', '/applications/{application_id}/commands/{command_id}',
            command_id = command_id,
            auth=True
        )

        return self.request(r, **kwargs)

    def edit_global_application_command(
        self,
        command_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        name_localizations: Optional[dict] = None,
        description_localizations: Optional[dict] = None,
        options: Optional[list[Union[dict, SlashOption]]] = None,
        default_permission: Optional[bool] = None,
        **kwargs
    ) -> Any:
        """
        Edit global application command
        """
        r = Route('PATCH', '/applications/{application_id}/commands/{command_id}',
            command_id = command_id,
            auth=True
        )

        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['description'] = description

        if name_localizations is not None:
            data['name_localizations'] = name_localizations

        if description_localizations is not None:
            data['description_localizations'] = description_localizations

        if options is not None:
            data['options'] = [asdict(o) if isinstance(o, SlashOption) else o for o in options]

        if default_permission is not None:
            data['default_permission'] = default_permission

        return self.request(r, 
            data=data
            **kwargs
        )

    def delete_global_application_command(
        self,
        command_id: int,
        **kwargs
    ) -> Any:
        """
        Delete global application command
        """
        r = Route('DELETE', '/applications/{application_id}/commands/{command_id}',
            command_id = command_id,
            auth=True
        )

        return self.request(r, **kwargs)

    def bulk_overwrite_global_application_commands(
        self,
        commands: list[dict],
        **kwargs
    ) -> Any:
        """
        Bulk overwrite global application commands
        """
        r = Route('PUT', '/applications/{application_id}/commands',
            auth=True
        )

        return self.request(r, 
            data=commands,
            **kwargs
        )
    
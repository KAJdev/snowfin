from typing import Any, Optional
import aiohttp
import json

import sanic

from snowfin.response import _DiscordResponse


from .errors import *

__all__ = (
    'HTTP',
    'Route'
)

class Route:
    BASE: str = "https://discord.com/api/v9"

    def __init__(self, method: str, path: str, **params) -> None:
        self.method: str = method
        self.path: str = path
        self.url: str = self.BASE + self.path
        if params:
            self.url = self.url.format_map(params)

class HTTP:
    """
    HTTP class
    """
    def __init__(
        self,
        proxy: Optional[str] = None,
        proxy_auth: Optional[aiohttp.BasicAuth] = None,
        headers: Optional[dict] = None
    ) -> None:
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
        _data: Optional[dict] = None,
        **kwargs
    ) -> Any:
        """
        Make a followup request
        """
        print(f"Requesting {route.method} {route.url} with {_data}")

        async with aiohttp.ClientSession() as session:
            async with session.request(
                route.method,
                route.url,
                headers=self.headers,
                proxy=self.proxy,
                proxy_auth=self.proxy_auth,
                json=_data if _data is not None else None,
                **kwargs
            ) as response:

                data = None
                text = await response.text(encoding='utf-8')
                try:
                    if response.headers['content-type'] == 'application/json':
                        data = json.loads(text)
                except KeyError:
                    pass

                if 300 > response.status >= 200:
                    return data

                if response.status == 403:
                    raise Forbidden(data)
                elif response.status == 404:
                    raise NotFound(data)
                elif response.status >= 500:
                    raise DiscordInternalError(data)
                else:
                    print(f"Unknown error: {response.status}")
                    raise HTTPException(data)

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
            application_id = request.ctx.application_id,
            interaction_token = request.ctx.token
        )

        return self.request(
            r,
            _data=response.to_dict().get('data', {}),
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
            application_id = request.ctx.application_id,
            interaction_token = request.ctx.token
        )

        data = response.to_dict().get('data', {})
        print(data)

        return self.request(
            r,
            _data=data,
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
            application_id = request.ctx.application_id,
            interaction_token = request.ctx.token
        )

        return self.request(
            r,
            **kwargs
        )

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
            application_id = request.ctx.application_id,
            interaction_token = request.ctx.token,
            message_id = message
        )

        return self.request(
            r,
            _data=response.to_dict().get('data', {}),
            **kwargs
        )

    
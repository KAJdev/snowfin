# snowfin
An async discord http interactions framework built on top of Sanic

## Installing
for now just install the package through pip via github
```sh
# Unix based
pip3 install git+https://github.com/kajdev/snowfin

# Windows
py -m pip install git+https://github.com/kajdev/snowfin
```

## Example

### Simple slash command
```python
import asyncio
import snowfin
from snowfin.client import AutoDefer
from snowfin.models import Interaction
from snowfin.response import MessageResponse

bot = snowfin.Client('public_key', 'application_id', 'token', auto_defer=AutoDefer(enabled=True, timeout=0, ephemeral=True))

@snowfin.slash_command(name="hello")
async def hello(context: Interaction):
    # we don't have to do anything, just don't return a response until we need to
    await asyncio.sleep(10)
    return MessageResponse('Ok, *Now* I want to respond ;)')

bot.run("0.0.0.0", 80, debug=True)
```

### Slash command with a deferred response
```python
import asyncio
import snowfin
from snowfin.models import Interaction
from snowfin.response import DeferredResponse, MessageResponse

bot = snowfin.Client('public_key', 'application_id', 'token', auto_defer=True)

@snowfin.slash_command(name="hello")
async def on_slash(context: Interaction):
    return DeferredResponse(on_slash_defer)

async def on_slash_defer(context: Interaction):
    await asyncio.sleep(1)
    return MessageResponse('Ok, *Now* I want to respond ;)')

bot.run("0.0.0.0", 80, debug=True)
```

## Links

- Library Docs (Coming Soon)
- Discord Server (Coming Soon)
- [Interaction Docs](https://discord.com/developers/docs/interactions/application-commands)

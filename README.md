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
import snowfin
from snowfin.response import MessageResponse

bot = snowfin.Client('public_key')

@snowfin.SlashCommand(name="hello")
async def on_slash(request):
    return MessageResponse('world')

bot.run("0.0.0.0", 80, debug=True)
```

### Slash command with a deferred response
```python
import asyncio
import snowfin
from snowfin.response import DeferredResponse, MessageResponse

bot = snowfin.Client('public_key')

@snowfin.SlashCommand(name="hello")
async def on_slash(request):
    return DeferredResponse(on_slash_defer)

async def on_slash_defer(request):
    await asyncio.sleep(1)
    return MessageResponse('Ok, *Now* I want to respond ;)')

bot.run("0.0.0.0", 80, debug=True)
```

## Links

- Library Docs (Coming Soon)
- Discord Server (Coming Soon)
- [Interaction Docs](https://discord.com/developers/docs/interactions/application-commands)

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

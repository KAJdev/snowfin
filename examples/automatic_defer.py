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

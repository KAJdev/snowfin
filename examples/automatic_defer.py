import asyncio
import snowfin
from snowfin.response import DeferredResponse, MessageResponse

bot = snowfin.Client('public_key', auto_defer=True, defer_ephemeral=True)

@snowfin.slash_command(name="hello")
async def hello(interaction):
    # we don't have to do anything, just don't return a response until we need to
    await asyncio.sleep(10)
    return MessageResponse('Ok, *Now* I want to respond ;)')


@snowfin.slash_command(name="world", auto_defer=False)
async def world(interaction):
    # we can override the setting per event, this will fail the interaction
    await asyncio.sleep(10)
    return MessageResponse('you will never see this!')


@snowfin.slash_command(name="long", defer_after=0)
async def always_long_command(interaction):
    # this will defer immediately
    await asyncio.sleep(10)
    return MessageResponse('wow this command always takes so long.')

bot.run("0.0.0.0", 80, debug=True)

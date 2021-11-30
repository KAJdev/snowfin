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
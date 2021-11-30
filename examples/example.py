import snowfin
from snowfin.response import MessageResponse

bot = snowfin.Client('public_key')

@snowfin.SlashCommand(name="hello")
async def on_slash(request):
    return MessageResponse('world')

bot.run("0.0.0.0", 80, debug=True)
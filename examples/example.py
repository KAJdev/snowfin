import snowfin
from snowfin.response import MessageResponse

bot = snowfin.Client('public_key')


@snowfin.slash_command(name="hello")
async def on_slash(interaction):
    return MessageResponse('world')

bot.run("0.0.0.0", 80, debug=True)

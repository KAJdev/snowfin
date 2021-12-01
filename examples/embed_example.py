import snowfin
from snowfin.response import MessageResponse
from snowfin.embed import Embed

bot = snowfin.Client('public_key')

@snowfin.SlashCommand(name="hello")
async def on_slash(request):
    return MessageResponse(embed=Embed(
        title="Embed Title",
        description="Embed Description",
        color=0x500000 # you can also pass in a Color class
    ))

bot.run("0.0.0.0", 80, debug=True)
import snowfin
from snowfin.components import Button
from snowfin.models import Interaction
from snowfin.response import MessageResponse

bot = snowfin.Client('public_key', 'application_id', 'token', auto_defer=True)

@snowfin.slash_command(name="hello")
async def on_slash(context: Interaction):
    """
    Slash command docstrings can be used for descriptions
    """

    return MessageResponse("Click this button!", Button(
        label="Click me!",
        custom_id="click_me",
    ))

@snowfin.component_callback("click_me")
async def on_click(context: Interaction):
    return MessageResponse(content="You clicked me!")

bot.run("0.0.0.0", 80, debug=True)

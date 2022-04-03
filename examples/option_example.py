import asyncio
import snowfin
from snowfin.client import AutoDefer
from snowfin.decorators import slash_command, slash_option
from snowfin.enums import OptionType
from snowfin.models import Interaction
from snowfin.response import MessageResponse

bot = snowfin.Client('public_key', 'application_id', 'token', auto_defer=AutoDefer(enabled=True, timeout=0, ephemeral=True))

@slash_command("hello")
@slash_option(name="option", description="this is a test option", type=OptionType.BOOLEAN)
async def hello(context: Interaction, option: bool = None):
    """
    Slash command docstrings can be used for descriptions
    """
    return MessageResponse(f"option: {option}")

bot.run("0.0.0.0", 80, debug=True)

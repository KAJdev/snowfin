import snowfin
from snowfin.components import TextInput
from snowfin.decorators import ModalCallback
from snowfin.models import Interaction
from snowfin.response import MessageResponse, ModalResponse

bot = snowfin.Client('public_key', 'application_id', 'token', auto_defer=True)

@snowfin.slash_command(name="hello")
async def on_slash(context: Interaction):
    """
    Slash command docstrings can be used for descriptions
    """

    return ModalResponse('modal_custom_id', 'Modal Title',
        TextInput('text_input_custom_id', 'Text Input Label')
    )

@snowfin.modal_callback("modal_custom_id")
async def on_submit(context: Interaction):
    return MessageResponse(content="You submitted me!")

bot.run("0.0.0.0", 80, debug=True)

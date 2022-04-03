from snowfin import Module, slash_command, slash_option, OptionType, Embed

class ExampleModule(Module):
    """This is an example module"""

    @slash_command("command")
    @slash_option(name="option", type=OptionType.STRING, description="example option")
    async def example_command(ctx, test: str = None):
        """this is a slash command in a module"""

        return "respond with a simple string for message content"

    @example_command.followup()
    async def example_command_followup(ctx, test: str = None):
        return "let's send a folloup message right after with an embed!", Embed(title="some embed title")

    def on_load(self):
        return super().on_load()

    def on_unload(self):
        return super().on_unload()
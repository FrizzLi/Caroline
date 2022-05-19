import os
from glob import glob

import discord
from discord.ext import commands


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=discord.Intents().all(),
            application_id=os.environ.get("CAROLINE_ID"),
        )

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )
        print(f"Logged as {bot.user.name} with {discord.__version__} version.")

    async def setup_hook(self):
        py_files = {
            os.path.basename(os.path.splitext(path)[0]):
            path for path in glob("cogs/*/*.py")
        }
        for dir_name in os.listdir("cogs"):
            if dir_name in py_files:
                try:
                    path = (
                        py_files[dir_name]
                        .replace("\\", ".")
                        .replace(".py", "")
                        .replace("/", ".")
                    )
                    await bot.load_extension(path)
                    print(f"{dir_name} module has been loaded.")
                except Exception as err:
                    print(f"{dir_name} module cannot be loaded. [{err}]")

        await bot.tree.sync(
            guild=discord.Object(id=os.environ.get("SERVER_ID"))
        )


PREFIX = "."
bot = MyBot()
bot.run(os.environ.get("CAROLINE_TOKEN"))

# TODO: Docstring
# TODO: Logs (instead of print)
# TODO: Tests

# TODO: Cogs configs into gitignore? Gsheets? Global problem tho
# TODO: Interaction cmds + check groups
# TODO: Restart bot cmd for refresh.. heroku CLI?

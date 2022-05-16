import glob
import os

import discord
from discord.ext import commands


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=prefix,
            intents=discord.Intents().all(),
            application_id=os.environ.get("CAROLINE_ID"),
        )

    @commands.Cog.listener()
    async def on_ready(ctx):
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online
        )
        print(
            f"Logged in as {bot.user.name} with {discord.__version__} version."
        )

    async def setup_hook(self):
        py_files = {
            os.path.basename(os.path.splitext(path)[0]): path
            for path in glob.glob("cogs/*/*.py")
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
                except Exception as e:
                    print(f"{dir_name} module cannot be loaded. [{e}]")

        await bot.tree.sync(
            guild=discord.Object(id=os.environ.get("SERVER_ID"))
        )


prefix = "."
bot = MyBot()
bot.run(os.environ.get("CAROLINE_TOKEN"))

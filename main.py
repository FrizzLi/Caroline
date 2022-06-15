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
        print(f"Logged {bot.user.name} with {discord.__version__} version.")

    async def setup_hook(self):
        py_files = {
            os.path.basename(os.path.splitext(path)[0]):
            path for path in glob("cogs/*/*.py")
        }
        for dir_name in os.listdir("cogs"):
            if dir_name in py_files:
                if PREFIX == PREFIXES[LOCAL] and dir_name in MB_LISTS[LOCAL]:
                    continue
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



HOST = 0
LOCAL = 1
PREFIXES = ("?", ".")
MB_LISTS = ((), ("music", "surveillance"))

try:
    import keep_alive
    keep_alive.keep_alive()
    TOKEN = os.environ.get("GLADOS_TOKEN")
    PREFIX = PREFIXES[HOST]
except ModuleNotFoundError:
    TOKEN = os.environ.get("CAROLINE_TOKEN")
    PREFIX = PREFIXES[LOCAL]

bot = MyBot()
bot.run(TOKEN)

# TODO: use all that I have in docs + check Python news, improve docs
# TODO: (ai -> music -> korean (priority)) - Deep check, ALL WHILE:
# clean + apply all python elements
# Git/VSCode deeper run (cheatsheet + docs improve)
# Docstring
# Logs (instead of print)
# Tests (+coverage)

# TODO: Interaction CMDs + check groups
# TODO: Restart bot CMD for refresh.. Heroku CLI?
# TODO: Ctrl+Shift+F "pylint:" errors, pylintrc

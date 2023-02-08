import os
from glob import glob

import discord
from discord.ext import commands
from dotenv import load_dotenv


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=discord.Intents().all(),
            application_id=APP_ID,
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
            os.path.basename(os.path.splitext(path)[0]): path
            for path in glob("cogs/*/*.py")
        }
        for dir_name in os.listdir("cogs"):
            if dir_name in py_files:
                if dir_name in BLACK_LIST:
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
            guild=discord.Object(id=os.environ["SERVER_ID"])
        )

load_dotenv()
if os.name == "nt":
    TOKEN = os.environ["CAROLINE_TOKEN"]
    APP_ID = os.environ["CAROLINE_ID"]
    BLACK_LIST = ("surveillance")
    PREFIX = "."
else:
    TOKEN = os.environ["GLADOS_TOKEN"]
    APP_ID = os.environ["GLADOS_ID"]
    BLACK_LIST = ("ai_algo")
    PREFIX = "?"

bot = MyBot()
bot.run(TOKEN)

# TODO: Polish Discord related stuff: Pylint, Document, Optimize code and Async
# TODO: Logs
# TODO: Resolve all weird pylint errors
# TODO: Tests (setup.py, pytest from reqs, AI: _apply_actions test (rmv), docs)

# TODO surveillance: Voice stats graphs, finish/remove on_presence_update
# TODO surveillance: Process old surveillance text and find info out of it

# TODO music: Track timestamps (how long the songs have been played instead of reqs)
# TODO music: Leaving the voice -> refresh still works.. polish that
# TODO music: Create radio bot,, automatically detects what ppl listen/request, 
# and just picks something out of it, or finds something to it (recommendation system!)

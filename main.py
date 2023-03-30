import json
import os
import sys
from glob import glob
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=BOTS_PREFIX,
            intents=discord.Intents().all(),
            application_id=BOTS_APP_ID,
        )
        self.channel_msg = ""

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

        msg = f"{bot.user.name} logged in with {discord.__version__} version."
        print(msg)

    async def setup_hook(self):
        py_files = {
            os.path.basename(os.path.splitext(path)[0]): path
            for path in glob("cogs/*/*.py")
        }
        for dir_name in os.listdir("cogs"):
            if dir_name in py_files:
                if dir_name in BOTS_BLACKLIST:
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

        await bot.tree.sync(guild=discord.Object(id=os.environ["SERVER_ID"]))

load_dotenv()
src_dir = Path(__file__).parents[0]
json_path = Path(f"{src_dir}/config.json")
with open(json_path, encoding="utf-8") as file:
    bots_settings = json.load(file)["bots_settings"]

if os.name == "nt" and len(sys.argv) < 2:
    BOTS_TOKEN = os.environ["CAROLINE_TOKEN"]
    BOTS_APP_ID = os.environ["CAROLINE_ID"]
    bot_settings = bots_settings["Caroline"]
else:
    BOTS_TOKEN = os.environ["GLADOS_TOKEN"]
    BOTS_APP_ID = os.environ["GLADOS_ID"]
    bot_settings = bots_settings["GLaDOS"]
BOTS_BLACKLIST = bot_settings["blacklist"]
BOTS_PREFIX = bot_settings["prefix"]

bot = MyBot()
bot.run(BOTS_TOKEN)

# TODO project template insp., also try others https://github.com/kkrypt0nn/Python-Discord-Bot-Template
# stopped at music.py TODO: [::], other priorities
# TODO music: Polish Discord related stuff: Pylint, Document, Optimize code and Async
# TODO music: Logs during polishing
# TODO korean: Polish Discord related stuff: Pylint, Document, Optimize code (TODOs there); commands from phone, applies to voice in pc bug

# TODO Apply ChatGPT opt. suggestions
# TODO (UPON NLP I guess) Script that explores all my python code, counts what and how many times i used certain methods along with their data struc.
# TODO Resolve all weird pylint errors
# TODO Tests (AI: setup.py, pytest from reqs, _apply_actions test (rmv), docs)
# TODO surveillance: Voice stats graphs, finish/remove on_presence_update
# TODO surveillance: Process old surveillance text and find info out of it
# TODO surveillance: Look into "did something" part
# TODO music: Track timestamps (how long the songs have been played instead of reqs)
# TODO music: Leaving the voice -> refresh still works.. polish that
# TODO music: Create radio bot,, automatically detects what ppl listen/request

# opt ideas: yield, slots, dict to namedtuple, # type: ignore (for mypy?) saw in rapptz

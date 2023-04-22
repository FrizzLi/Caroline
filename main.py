import json
import os
import sys
from glob import glob
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv


class MyBot(commands.Bot):
    def __init__(self, variables):
        super().__init__(
            command_prefix=variables["prefix"],
            application_id=variables["app_id"],
            intents=discord.Intents().all(),
        )
        self.cog_blacklist = variables["cog_blacklist"]

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
                if dir_name in self.cog_blacklist:
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

        # is this necessary? SERVER_ID
        await bot.tree.sync(guild=discord.Object(id=os.environ["SERVER_ID"]))

def load_essentials():
    """_summary_

    _extended_summary_

    Returns:
        _type_: _description_
    """

    error_msgs = ""

    src_dir = Path(__file__).parents[0]
    json_path = Path(f"{src_dir}/config.json")
    if Path(json_path).is_file():
        with open(json_path, encoding="utf-8") as file:
            bots_settings = json.load(file)["bots_settings"]
    else:
        error_msgs += "'config.json' not found!\n"

    if os.name == "nt" and len(sys.argv) < 2:
        bot_name = "Caroline"
    else:
        bot_name = "GLaDOS"

    token = os.environ[f"{bot_name}_TOKEN"]
    app_id = os.environ[f"{bot_name}_ID"]
    prefix = bots_settings[bot_name]["prefix"]
    if not token:
        error_msgs += f"{bot_name}'s token in .env file is not set!\n"
    if not app_id:
        error_msgs += f"{bot_name}'s app ID in .env file is not set!\n"
    if not prefix:
        error_msgs += "prefix in config.json is not set!\n"
    if error_msgs:
        sys.exit(error_msgs)

    return {
        "token": token,
        "app_id": app_id,
        "prefix": prefix,
        "cog_blacklist": bots_settings[bot_name]["cog_blacklist"]
    }

load_dotenv()
bot_vars = load_essentials()

bot = MyBot(bot_vars)
bot.run(bot_vars["token"])

# TODO project template insp., also try others https://github.com/kkrypt0nn/Python-Discord-Bot-Template
# TODO surveillance: Look into "did something" part
# TODO check docs + linting outside of music + korean cogs
# TODO look for other bots inspiration for music bots
# opt ideas: yield, dict to namedtuple, # type: ignore (for mypy?) saw in rapptz

# stopped at music.py TODO: [::]
# TODO music: Logs during polishing (use wrappers?)
# TODO music: Polish Discord related stuff: Pylint, Document, Optimize code and Async
# TODO music: Leaving the voice -> refresh still works.. polish that
# TODO korean: Polish Discord related stuff: Pylint, Document, Optimize code
# TODO korean: update sheets when the session is over, not when it starts -> polish that whole function

# TODO Apply ChatGPT opt. suggestions
# TODO Script that explores all my python code, counts what and how many times i used certain methods along with their data struc.

# TODO ALL: Pylint - resolve all errors
# TODO ai_algo: Tests (_apply_actions test (rmv), docs)
# TODO korean: Word by word mp3, to make sound for two words.. or remove two words?..
# TODO music: Create radio (automatically picks songs)
# TODO surveillance: Voice stats graphs, Process old logs


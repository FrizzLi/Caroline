import os
import sys
from datetime import datetime
from glob import glob

import discord
import pytz
from discord.ext import commands, tasks
from dotenv import load_dotenv


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=discord.Intents().all(),
            application_id=APP_ID,
        )
        self.channel_msg = ""

    def get_time(self):
        """Gets current time based in Bratislava for logging.

        Returns:
            str: datetime in "Year-Month-Day Time" format
        """

        time = datetime.now(pytz.timezone("Europe/Bratislava"))
        time = time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    def get_log_channel(self):
        """Gets surveillance text channel.

        Returns:
            discord.channel.TextChannel: "🎥surveillance" text channel
        """

        channel_id = int(os.environ["SURVEILLANCE_CHANNEL_ID"])  # int?
        return self.get_channel(channel_id)

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

        self.test.start()

        surveillance_channel = self.get_log_channel()
        time = self.get_time()
        msg = f"{time}: {bot.user.name} logged in with {discord.__version__} version."
        await surveillance_channel.send(msg)
        print(msg)

    async def close(self):
        surveillance_channel = self.get_log_channel()
        time = self.get_time()
        await surveillance_channel.send(f"{time}: {self.user.name} has gone offline successfully!")
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.invisible,
        )
        await super().close()

    @tasks.loop(minutes=5)
    async def test(self):
        surveillance_channel = self.get_log_channel()
        time = self.get_time()
        msg = f"{time}: {bot.user.name} is online."
        if self.channel_msg:
            await self.channel_msg.delete()

        self.channel_msg = await surveillance_channel.send(msg)

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
if os.name == "nt" and len(sys.argv) < 2:
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

# TODO music: Polish Discord related stuff: Pylint, Document, Optimize code and Async
# TODO music: Logs during polishing
# TODO korean: Polish Discord related stuff: Pylint, Document, Optimize code (TODOs there)

# TODO Resolve all weird pylint errors
# TODO Tests (AI: setup.py, pytest from reqs, _apply_actions test (rmv), docs)
# TODO surveillance: Voice stats graphs, finish/remove on_presence_update
# TODO surveillance: Process old surveillance text and find info out of it
# TODO surveillance: Look into "did something" part
# TODO music: Track timestamps (how long the songs have been played instead of reqs)
# TODO music: Leaving the voice -> refresh still works.. polish that
# TODO music: Create radio bot,, automatically detects what ppl listen/request
# and just picks something out of it, or finds something to it (recommendation system!)

# opt ideas: yield, slots, dict to namedtuple

import discord
import json
import os
import glob
import asyncio

from discord.ext import commands

with open("config.json", "r") as f:
    gconfig = json.load(f)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="?",
            intents=discord.Intents().all(),
            application_id=655460915281657877
        )

    # async def close(self):
    #     await super().close()
    #     await self.session.close()

    # TODO: https://www.youtube.com/watch?v=U0Us5NHG-nY easier class

    @commands.Cog.listener()
    async def on_command_error(ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("BadArgument! [{}]".format(error))
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("MissingRequiredArgument! [{}]".format(error))
        else:
            await ctx.send(error)


    @commands.Cog.listener()
    async def on_ready(ctx):
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"?help",
            ),
            # status=discord.Status.invisible
        )
        print(
            f"Logged in as {bot.user.name} with {discord.__version__} version."
        )



    @commands.Cog.listener()  # brief=[f for f in os.listdir("cogs")]
    async def load(ctx, cog: str):
        try:
            bot.load_extension(f"cogs.{cog}.{cog}")
            await ctx.send(f"Loaded cog: {cog}")
        except Exception as error:
            await ctx.send(f"{cog} cannot be loaded. [{error}]")


    @commands.Cog.listener()
    async def unload(ctx, cog: str):
        try:
            bot.unload_extension(f"cogs.{cog}.{cog}")
            await ctx.send(f"Unloaded cog: {cog}")
        except Exception as error:
            await ctx.send(f"{cog} cannot be unloaded. [{error}]")

    # async def load_extensions():

    #     await bot.tree.sync(guild=discord.Object(id=553636358137053199))

    async def setup_hook(self):
        # self.session = aiohttp.ClientSession()

        py_files = {
            os.path.basename(os.path.splitext(path)[0]): path
            for path in glob.glob("cogs/*/*.py")
        }
        for dir_name in os.listdir("cogs"):
            if dir_name in py_files:
                try:
                    path = py_files[dir_name].replace("\\", ".").replace(".py", "")
                    await bot.load_extension(path)
                    print(f"{dir_name} module has been loaded.")
                except Exception as e:
                    print(f"{dir_name} module cannot be loaded. [{e}]")
        # Change 456 to your server/guild id
        await bot.tree.sync(guild=discord.Object(id=553636358137053199))

# async def main():
#     bot = MyBot()
#     async with bot:
#         await bot.start(gconfig["token"])

# if __name__ == "__main__":
#     # bot = MyBot()
#     asyncio.run(main())


bot = MyBot()
bot.run(gconfig["token"])

# NOTE: Test scenarios for audio download:
# Youtube song/playlist + dl while playing,
# Spotify song/playlist + dl while playing,

# TODO:
# Polish functionality (fix all bugs) in Caroline
# - add hint ctx.prefix
# - write command that shows whats working
# - add listening up to lvl3
# - add bigger buttons (need new version of dc or sth)

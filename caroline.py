import discord
import json
import os
import glob
import asyncio

from discord.ext import commands

with open("config.json", "r") as f:
    gconfig = json.load(f)

intents = discord.Intents().all()
prefix = "?"
bot = commands.Bot(command_prefix=prefix, intents=intents)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("BadArgument! [{}]".format(error))
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("MissingRequiredArgument! [{}]".format(error))
    else:
        await ctx.send(error)


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{prefix}help",
        ),
        status=discord.Status.invisible
    )
    print(
        f"Logged in as {bot.user.name} with {discord.__version__} version."
    )



@bot.command(brief=[f for f in os.listdir("cogs")])
async def load(ctx, cog: str):
    try:
        bot.load_extension(f"cogs.{cog}.{cog}")
        await ctx.send(f"Loaded cog: {cog}")
    except Exception as error:
        await ctx.send(f"{cog} cannot be loaded. [{error}]")


@bot.command()
async def unload(ctx, cog: str):
    try:
        bot.unload_extension(f"cogs.{cog}.{cog}")
        await ctx.send(f"Unloaded cog: {cog}")
    except Exception as error:
        await ctx.send(f"{cog} cannot be unloaded. [{error}]")

async def load_extensions():
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

async def main():
    async with bot:
        await load_extensions()
        await bot.start(gconfig["token"])

if __name__ == "__main__":
    asyncio.run(main())

# NOTE: Test scenarios for audio download:
# Youtube song/playlist + dl while playing,
# Spotify song/playlist + dl while playing,

# TODO:
# Polish functionality (fix all bugs) in Caroline
# - add hint ctx.prefix
# - write command that shows whats working
# - add listening up to lvl3
# - add bigger buttons (need new version of dc or sth)

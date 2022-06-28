import random

import discord
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Rolls a number between 1 and 100. (roll 1000)")
    async def roll(self, ctx, max_=100):
        rolled_number = f"{str(random.randint(1, max_))} (1 - {str(max_)})"
        await ctx.send(f"{ctx.message.author.mention} rolls {rolled_number}")

    @commands.command(brief="Enables Python interactive shell.")
    async def python(self, ctx):
        await ctx.send(f'Python mode activated! Exit by "{ctx.prefix}"')
        await self.bot.change_presence(activity=discord.Game(name="Python"))

        def check(message):
            return message.channel == ctx.channel

        msg = await self.bot.wait_for("message", check=check)
        ans = 0

        while not msg.content.startswith(f"{ctx.prefix}"):
            try:  # with return
                ans = eval(msg.content)
                await ctx.send(ans)
            except Exception:  # no return
                try:
                    exec(msg.content)
                except Exception as err:  # invalid input
                    await ctx.send(err)
            msg = await self.bot.wait_for("message", check=check)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=f"{ctx.prefix}help"
            )
        )
        await ctx.send("Python mode deactivated!")


async def setup(bot):
    await bot.add_cog(Commands(bot))

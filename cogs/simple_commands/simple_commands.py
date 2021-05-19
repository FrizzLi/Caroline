import random

import discord
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(brief="Rolls a number between 1 and 100. (roll 1000)")
    async def roll(self, ctx, max_=100):
        rolled_number = f"{str(random.randint(1, max_))} (1 - {str(max_)})"
        await ctx.send(f"{ctx.message.author.mention} rolls {rolled_number}")

    @commands.command(brief="Enables Python interactive shell.")
    async def python(self, ctx):
        await ctx.send(f'Python mode activated! Exit by "{ctx.prefix}"')
        await self.client.change_presence(activity=discord.Game(name="Python"))

        def check(message):
            return message.channel == ctx.channel

        msg = await self.client.wait_for("message", check=check)
        ans = 0

        while not msg.content.startswith(f"{ctx.prefix}"):
            try:  # evaluating input with value return
                ans = eval(msg.content)
                await ctx.send(ans)
            except Exception:  # executing input without return
                try:
                    exec(msg.content)
                except Exception as e2:  # invalid input
                    await ctx.send(e2)
            msg = await self.client.wait_for("message", check=check)

        await self.client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=f"{ctx.prefix}help"
            )
        )
        await ctx.send("Python mode deactivated!")

    @commands.command(brief="Deletes specified number of messages. (clear 5)")
    async def clear(self, ctx, amount=5):
        channel = ctx.message.channel
        async for message in channel.history(limit=int(amount) + 1):
            await message.delete()

    @commands.command(brief="?choose black pink white.")
    async def choose(self, ctx, *args):
        await ctx.send(random.choice(args))

    @commands.command(brief="Replies specified message.++")
    async def echo(self, ctx, *args):
        """ For voice put '-v' after echo. E.g. ?echo -v Hello world!"""
        # TODO: after voice is done, make TTS

        if args[0] == "-v":
            await ctx.send(" ".join(args[1:]), tts=True)
        else:
            await ctx.send(" ".join(args))

    @commands.command(brief="Logouts bot from the server.")
    async def close(self, ctx):
        await self.client.close()


def setup(client):
    client.add_cog(Commands(client))

import random
from datetime import datetime

import discord
import pytz
from discord.ext import commands


class Surveillance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self):
        return self.bot.get_channel(1058633423301902429)

    def get_time(self):
        time = datetime.now(pytz.timezone("Europe/Bratislava"))
        time = time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    # @commands.Cog.listener()
    # async def on_presence_update(self, before, after):
    #     before_offline = before.status == discord.Status.offline
    #     after_offline = after.status == discord.Status.offline
    #     before_idle = before.status == discord.Status.idle
    #     after_idle = after.status == discord.Status.idle
    #     before_dnd = before.status == discord.Status.dnd
    #     after_dnd = after.status == discord.Status.dnd
    #     diff_act = before.activity != after.activity
    #     before_no_act = before.activity is None
    #     after_no_act = after.activity is None

    #     time = self.get_time()
    #     #     # if before_offline and not after_offline:
    #     #     #     msg = "has come online."
    #     #     # elif not before_offline and after_offline:
    #     #     #     msg = "has gone offline."
    #     if diff_act and before_no_act:
    #         if after.activity.name:
    #             msg = f"has started {after.activity.name}."
    #             msg = f"{time}: {after.name} {msg}"
    #             await self.get_log_channel().send(msg)
    #     elif diff_act and after_no_act:
    #         if before.activity.name:
    #             msg = f"has stopped {before.activity.name}."
    #             msg = f"{time}: {after.name} {msg}"
    #             await self.get_log_channel().send(msg)
    #     #     # elif not before_dnd and after_dnd:
    #     #     #     msg = "has set DND status."
    #     #     # elif before_dnd and not after_dnd:
    #     #     #     msg = "is no longer DND."
    #     #     # elif before_idle and not after_idle:
    #     #     #     msg = "is no longer idle."
    #     #     # elif not before_idle and after_idle:
    #     #     #     msg = "has gone idle."
    #     # else:
    #         # print(f"{after.name} did something..!")
    #         # return

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        deaf = not before.deaf and after.deaf
        no_deaf = before.deaf and not after.deaf
        mute = not before.mute and after.mute
        no_mute = before.mute and not after.mute
        self_deaf = not before.self_deaf and after.self_deaf
        self_no_deaf = before.self_deaf and not after.self_deaf
        self_mute = not before.self_mute and after.self_mute
        self_no_mute = before.self_mute and not after.self_mute
        video = not before.self_video and after.self_video
        no_video = before.self_video and not after.self_video
        stream = not before.self_stream and after.self_stream
        no_stream = before.self_stream and not after.self_stream
        afk = not before.afk and after.afk
        no_afk = before.afk and not after.afk
        left = before.channel != after.channel and after.channel is None
        join = before.channel != after.channel and before.channel is None
        move = before.channel != after.channel

        if deaf or self_deaf:
            msg = "has been deafened."
        elif no_deaf or self_no_deaf:
            msg = "has been undeafened."
        elif mute or self_mute:
            msg = "has been muted."
        elif no_mute or self_no_mute:
            msg = "has been unmuted."
        elif video:
            msg = "has enabled camera."
        elif no_video:
            msg = "has stopped camera."
        elif stream:
            msg = "has started streaming."
        elif no_stream:
            msg = "has stopped streaming."
        elif afk:
            msg = "has gone afk."
        elif no_afk:
            msg = "is no longer afk."
        elif left:
            msg = f"has left {before.channel} channel."
        elif join:
            msg = f"has joined {after.channel} channel."
        elif move:
            msg = f"has moved from {before.channel} to {after.channel}."
        else:
            print(f"{member.name} did something..!")
            return

        time = self.get_time()
        await self.get_log_channel().send(f"{time}: {member.name} {msg}")

    # Simple commands
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
                ans = eval(msg.content)  # pylint: disable=eval-used
                await ctx.send(ans)
            except SyntaxError:
                #  no return
                try:
                    exec(msg.content)  # pylint: disable=exec-used
                except Exception as err:  # pylint: disable=broad-except
                    # invalid input
                    await ctx.send(err)
            msg = await self.bot.wait_for("message", check=check)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=f"{ctx.prefix}help"
            )
        )
        await ctx.send("Python mode deactivated!")


async def setup(bot):
    await bot.add_cog(Surveillance(bot))

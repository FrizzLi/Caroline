import contextlib
import io
import textwrap
from datetime import datetime

import discord
import pytz
from discord.ext import commands


class Surveillance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.local_vars = {"self": self}

    def get_log_channel(self):
        return self.bot.get_channel(1058633423301902429)

    def get_time(self):
        time = datetime.now(pytz.timezone("Europe/Bratislava"))
        time = time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    def get_code(self, msg):
        if msg.startswith("```") and msg.endswith("```"):
            code = "\n".join(msg.split("\n")[1:])[:-3]
            code += "\nreturn locals()"
            code = textwrap.indent(code, "  ")
            return code
        else:
            err_msg = ("Your input must start with a code block! "
                       r"Write it as \`\`\`<code>\`\`\`!")
            raise Exception(err_msg)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        deaf = not before.deaf and after.deaf
        deaf_not = before.deaf and not after.deaf
        self_deaf = not before.self_deaf and after.self_deaf
        self_deaf_not = before.self_deaf and not after.self_deaf
        mute = not before.mute and after.mute
        mute_not = before.mute and not after.mute
        self_mute = not before.self_mute and after.self_mute
        self_mute_not = before.self_mute and not after.self_mute
        left = before.channel != after.channel and after.channel is None
        join = before.channel != after.channel and before.channel is None
        video = not before.self_video and after.self_video
        video_not = before.self_video and not after.self_video
        stream = not before.self_stream and after.self_stream
        stream_not = before.self_stream and not after.self_stream
        afk = not before.afk and after.afk
        afk_not = before.afk and not after.afk
        move = before.channel != after.channel

        possible_state_changes = {
            "has been deafened.": deaf or self_deaf,
            "has been undeafened.": deaf_not or self_deaf_not,
            "has been muted.": mute or self_mute,
            "has been unmuted.": mute_not or self_mute_not,
            "has enabled camera.": video,
            "has stopped camera.": video_not,
            "has started streaming.": stream,
            "has stopped streaming.": stream_not,
            "has gone afk.": afk,
            "is no longer afk.": afk_not,
            f"has left {before.channel} channel.": left,
            f"has joined {after.channel} channel.": join,
            f"has moved from {before.channel} to {after.channel}.": move
        }

        msg = change = ""
        for msg, change in possible_state_changes.items():
            if change:
                break
        if not change:
            print(f"{member.name} did something..!")
            return

        time = self.get_time()
        await self.get_log_channel().send(f"{time}: {member.name} {msg}")

    @commands.command(brief="Enables Python interactive shell.")
    async def python1(self, ctx, *, msg):
        self.local_vars["ctx"] = ctx

        try:
            code = self.get_code(msg)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exec(f"async def func():\n{code}", self.local_vars)  # pylint: disable=exec-used
                new_local_vars = await self.local_vars["func"]()
                self.local_vars.update(new_local_vars)
                result = stdout.getvalue()
                if len(result) > 1990:
                    warning_msg = ("The output has been shortened "
                                   "because it was too long.\n")
                    result = warning_msg + result[:1900]
        except Exception as err:  # pylint: disable=broad-except
            result = err
        await ctx.send(f"```py\n{result}```")

    @commands.command(brief="Enables Python interactive shell.")
    async def python3(self, ctx):
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

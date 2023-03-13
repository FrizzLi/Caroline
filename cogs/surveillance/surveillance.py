"""This module serves to run Python code through a message and surveillance
system which tracks activity on all voice channels on the Discord server.
"""

import contextlib
import io
import os
import textwrap
from datetime import datetime

import discord
import pytz
from discord.ext import commands, tasks


class Surveillance(commands.Cog):
    """Represents cog extension that tracks activity on all voice channels
    and also allows us to run Python code.

    Args:
        commands (discord.ext.commands.cog.CogMeta): class that is taken to
            create subclass - our own customized cog module
    """

    __slots__ = ("bot", "local_vars")

    def __init__(self, bot):
        self.bot = bot
        self.local_vars = {"self": self}
        self.channel_msg = ""

    # Helping methods
    def get_code(self, message):
        """Cleanses the message to a pure code ready to be executed.

        It removes the first line that contains the command call and
        the block characters surrounding the code itself (```<code>```).
        In addition, it wraps the code into function and returns local
        variables that are going to be stored for next command call.

        Args:
            message (str): message that contains the command and code in block

        Raises:
            Exception: the code is not inside a block (```<code>```)

        Returns:
            str: executable code
        """

        if message.startswith("```") and message.endswith("```"):
            code = "\n".join(message.split("\n")[1:])[:-3]
            code += "\nreturn locals()"
            code = textwrap.indent(code, "  ")
            code = "async def func():\n" + code
            return code
        else:
            err_msg = (
                "Your input must start with a code block! "
                r"Write it as \`\`\`<code>\`\`\`!"
            )
            raise Exception(err_msg)

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

        channel_id = int(os.environ["SURVEILLANCE_CHANNEL_ID"])
        print(channel_id)
        return self.bot.get_channel(channel_id)

    @tasks.loop(minutes=5)
    async def test(self):
        surveillance_channel = self.get_log_channel()
        time = self.get_time()
        msg = f"{time}: {self.bot.user.name} is online."
        if self.channel_msg:
            await self.channel_msg.delete()

        self.channel_msg = await surveillance_channel.send(msg)

    @commands.Cog.listener()
    async def on_ready(self):
        self.test.start()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Tracks every voice channel action of all people on the server.

        It writes action's information into log text channel.
        The information includes time, person's name and the action itself.

        Args:
            member (discord.member.Member): person that acts
            before (discord.member.VoiceState): person's voice state
            after (discord.member.VoiceState): person's voice state
        """

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
            f"has moved from {before.channel} to {after.channel}.": move,
        }

        msg = change = ""
        for msg, change in possible_state_changes.items():
            if change:
                break
        if not change:
            print(f"{member.name} did something..!")
            return

        time = self.bot.get_time()
        await self.bot.get_log_channel().send(f"{time}: {member.name} {msg}")

    @commands.command(aliases=["py"])
    async def python(self, ctx, *, message):
        """Executes Python code that was written in a block of the message.

        Args:
            ctx (discord.ext.commands.context.Context): context (old commands)
            message (str): message that contains the command and code in block
        """

        self.local_vars["ctx"] = ctx

        try:
            code = self.get_code(message)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exec(code, self.local_vars)  # pylint: disable=exec-used
                new_local_vars = await self.local_vars["func"]()
                self.local_vars.update(new_local_vars)

                result = stdout.getvalue()
                if len(result) > 1990:
                    warning_msg = (
                        "The output has been shortened "
                        "because it was too long.\n"
                    )
                    result = warning_msg + result[:1900]
        except Exception as err:  # pylint: disable=broad-except
            result = err
        await ctx.send(f"```py\n{result}```")


async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        Surveillance(bot), guilds=[discord.Object(id=os.environ["SERVER_ID"])]
    )

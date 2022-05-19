import json
import os
from datetime import datetime

import discord
import pytz
from discord.ext import commands
from discord.utils import get


class Surveillance(commands.Cog):
    def __init__(self, bot):
        surv_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f"{surv_dir}\\surv_config.json", "r") as cf:
            config = json.load(cf)

        self.bot = bot
        self.config = config

    def get_log_channel(self):
        return self.bot.get_channel(self.config["IDs"]["logs"])

    def get_time(self):
        time = datetime.now(pytz.timezone("Europe/Bratislava"))
        time = time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        time = self.get_time()

        # dont check nicks, but username instead as its more stable
        # do not allow users to change nicknames into already existing ones
        if before.nick != after.nick:
            member_exist = get(after.guild.members, name=after.display_name)
            if after.nick and member_exist:
                await after.edit(nick=(before.display_name + "_stop"))

            new_nick = after.name if not after.nick else after.nick
            await self.get_log_channel().send(
                f"{time}: {before.name} has changed his nick to {new_nick}."
            )

        if (
            before.status == discord.Status.offline
        ) and after.status != discord.Status.offline:
            await self.get_log_channel().send(
                f"{time}: {after.name} has come online."
            )
        if (
            before.status == discord.Status.idle
        ) and after.status != discord.Status.idle:
            await self.get_log_channel().send(
                f"{time}: {after.name} is no longer idle."
            )
        if (
            before.status != discord.Status.dnd
        ) and after.status == discord.Status.dnd:
            await self.get_log_channel().send(
                f"{time}: {after.name} has set DND status."
            )
        if (
            before.status == discord.Status.dnd
        ) and after.status != discord.Status.dnd:
            await self.get_log_channel().send(
                f"{time}: {after.name} is no longer DND."
            )
        if (
            before.status != discord.Status.idle
        ) and after.status == discord.Status.idle:
            await self.get_log_channel().send(
                f"{time}: {after.name} has gone idle."
            )
        elif before.activity != after.activity and after.activity is None:
            await self.get_log_channel().send(
                f"{time}: {after.name} has stopped {before.activity.name}."
            )
        elif before.activity != after.activity and before.activity is None:
            await self.get_log_channel().send(
                f"{time}: {after.name} has started {after.activity.name}."
            )
        if (
            before.status != discord.Status.offline
        ) and after.status == discord.Status.offline:
            await self.get_log_channel().send(
                f"{time}: {after.name} has gone offline."
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        time = self.get_time()

        if ((before.deaf is False) and after.deaf) or (
            (before.self_deaf is False) and after.self_deaf
        ):
            await self.get_log_channel().send(
                f"{time}: {member.name} has been deafened."
            )
        elif ((before.deaf is True) and not after.deaf) or (
            (before.self_deaf is True) and not after.self_deaf
        ):
            await self.get_log_channel().send(
                f"{time}: {member.name} has been undeafened."
            )
        elif ((before.mute is False) and after.mute) or (
            (before.self_mute is False) and after.self_mute
        ):
            await self.get_log_channel().send(
                f"{time}: {member.name} has been muted."
            )
        elif ((before.mute is True) and not after.mute) or (
            (before.self_mute is True) and not after.self_mute
        ):
            await self.get_log_channel().send(
                f"{time}: {member.name} has been unmuted."
            )
        elif (before.self_video is False) and after.self_video:
            await self.get_log_channel().send(
                f"{time}: {member.name} has started broadcasting a video."
            )
        elif (before.self_video is True) and not after.self_video:
            await self.get_log_channel().send(
                f"{time}: {member.name} has stopped broadcasting a video."
            )
        elif (before.afk is False) and after.afk:
            await self.get_log_channel().send(
                f"{time}: {member.name} has gone afk."
            )
        elif (before.afk is True) and not after.afk:
            await self.get_log_channel().send(
                f"{time}: {member.name} is no longer afk."
            )
        elif before.channel != after.channel and after.channel is None:
            await self.get_log_channel().send(
                f"{time}: {member.name} has left {before.channel} channel."
            )
        elif before.channel != after.channel and before.channel is None:
            await self.get_log_channel().send(
                f"{time}: {member.name} has joined {after.channel} channel."
            )
        elif before.channel != after.channel:
            await self.get_log_channel().send(
                f"{time}: {member.name} has moved from {before.channel} channel into {after.channel}."
            )

    # More types of actions:
    # DELETED msg_post (when somebody sends a message),
    # DELETED msg_delete (somebody deletes a message),
    # DELETED msg_edit (somebody edits a message),
    # DELETED on_typing (somebody starts writing into channel),
    # DELETED reaction_add (somebody adds a reaction to message),
    # DELETED reaction_remove (somebody removes a reaction from message),
    # DELETED member_join (somebody has joined the server),
    # DELETED member_remove (somebody has left the server),
    # member_update (nick change, on/off, dnd, idle, activity),
    # member_voice (deaf, mute, broadcast, afk, join/move voice channel),
    # DELETED member_role (shows user's role after name)

    # TODO: Config with Gsheets
    @commands.is_owner()
    @commands.command(brief="Bypass surveillance settings.++")
    async def bypass(self, ctx, channel=None, val=None):
        """ "?bypass <channel_name> 1" - adds channel for bypassing
        "?bypass <channel_name> 0" - removes channel from bypassing"""

        if channel and val:
            val = "1" if val != "0" else "0"
            if val == "1" and channel in self.config["bypass_channels"]:
                return await ctx.send(
                    f'"{channel}" channel is already being bypassed!'
                )
            elif val == "0" and channel not in self.config["bypass_channels"]:
                return await ctx.send(
                    f'"{channel}" channel isnt bypassed!'
                )

            if val != "0":
                self.config["bypass_channels"].append(channel)
                msg = f"{channel} channel is now being untracked."
            else:
                self.config["bypass_channels"].remove(channel)
                msg = f"{channel} channel is now being tracked."

            surv_dir = os.path.dirname(os.path.abspath(__file__))
            with open(surv_dir + "\\surv_config.json", "w") as f4:
                json.dump(self.config, f4, sort_keys=True, indent=4)

            await self.get_log_channel().send(msg)
            return await ctx.send(msg)

        else:  # display current bypass settings
            embed = discord.Embed(colour=discord.Colour.blue())
            embed.add_field(
                name="Bypass configuration",
                value=self.config["bypass_channels"],
            )
            return await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Surveillance(bot))

# TODO: Helping method for stats observing in graphs

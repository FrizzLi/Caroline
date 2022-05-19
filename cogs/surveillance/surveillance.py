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
    async def on_presence_update(self, before, after):

        off     = (before.status != discord.Status.offline) and after.status == discord.Status.offline
        no_off  = (before.status == discord.Status.offline) and after.status != discord.Status.offline
        idle    = (before.status != discord.Status.idle) and after.status == discord.Status.idle
        no_idle = (before.status == discord.Status.idle) and after.status != discord.Status.idle
        dnd     = (before.status != discord.Status.dnd) and after.status == discord.Status.dnd
        no_dnd  = (before.status == discord.Status.dnd) and after.status != discord.Status.dnd
        act     = before.activity != after.activity and before.activity is None
        no_act  = before.activity != after.activity and after.activity is None

        msgs = []
        if off:
            msgs.append("has come online.")
        if no_idle:
            msgs.append("is no longer idle.")
        if dnd:
            msgs.append("has set DND status.")
        if no_dnd:
            msgs.append("is no longer DND.")
        if idle:
            msgs.append("has gone idle.")
        elif no_act:
            msgs.append(f"has stopped {before.activity.name}.")
        elif act:
            msgs.append(f"has started {after.activity.name}.")
        if no_off:
            msgs.append("has gone offline.")

        time = self.get_time()
        for msg in msgs:
            await self.get_log_channel().send(f"{time}: {after.name} {msg}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        deaf    = ((before.deaf is False) and after.deaf) or ((before.self_deaf is False) and after.self_deaf)
        no_deaf = ((before.deaf is True) and not after.deaf) or ((before.self_deaf is True) and not after.self_deaf)
        mute    = ((before.mute is False) and after.mute) or ((before.self_mute is False) and after.self_mute)
        no_mute = ((before.mute is True) and not after.mute) or ((before.self_mute is True) and not after.self_mute)
        bcast   = (before.self_video is False) and after.self_video
        no_bcast = (before.self_video is True) and not after.self_video
        afk     = (before.afk is False) and after.afk
        no_afk  = (before.afk is True) and not after.afk
        left    = before.channel != after.channel and after.channel is None
        join    = before.channel != after.channel and before.channel is None
        move    = before.channel != after.channel

        msgs = []
        if deaf:
            msgs.append("has been deafened.")
        elif no_deaf:
            msgs.append("has been undeafened.")
        elif mute:
            msgs.append("has been muted.")
        elif no_mute:
            msgs.append("has been unmuted.")
        elif bcast:
            msgs.append("has started broadcasting a video.")
        elif no_bcast:
            msgs.append("has stopped broadcasting a video.")
        elif afk:
            msgs.append("has gone afk.")
        elif no_afk:
            msgs.append("is no longer afk.")
        elif left:
            msgs.append(f"has left {before.channel} channel.")
        elif join:
            msgs.append(f"has joined {after.channel} channel.")
        elif move:
            msgs.append(f"has moved from {before.channel} channel into {after.channel}.")

        time = self.get_time()
        for msg in msgs:
            await self.get_log_channel().send(f"{time}: {after.name} {msg}")

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

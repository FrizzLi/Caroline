import json
import os
from datetime import datetime

import discord
import pytz
from discord.ext import commands
from discord.utils import get


class Surveillance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self):
        return self.bot.get_channel(556514691069902870)

    def get_time(self):
        time = datetime.now(pytz.timezone("Europe/Bratislava"))
        time = time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        off     = before.status != discord.Status.offline and after.status == discord.Status.offline
        no_off  = before.status == discord.Status.offline and after.status != discord.Status.offline
        idle    = before.status != discord.Status.idle and after.status == discord.Status.idle
        no_idle = before.status == discord.Status.idle and after.status != discord.Status.idle
        dnd     = before.status != discord.Status.dnd and after.status == discord.Status.dnd
        no_dnd  = before.status == discord.Status.dnd and after.status != discord.Status.dnd
        act     = before.activity != after.activity and before.activity is None
        no_act  = before.activity != after.activity and after.activity is None

        if no_off:
            msg = "has come online."
        elif off:
            msg = "has gone offline."
        elif no_act:
            msg = f"has stopped {before.activity.name}."
        elif act:
            msg = f"has started {after.activity.name}."
        elif dnd:
            msg = "has set DND status."
        elif no_dnd:
            msg = "is no longer DND."
        elif no_idle:
            msg = "is no longer idle."
        elif idle:
            msg = "has gone idle."

        time = self.get_time()
        await self.get_log_channel().send(f"{time}: {after.name} {msg}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        deaf    = (not before.deaf and after.deaf) or (not before.self_deaf and after.self_deaf)
        no_deaf = (before.deaf and not after.deaf) or (before.self_deaf and not after.self_deaf)
        mute    = (not before.mute and after.mute) or (not before.self_mute and after.self_mute)
        no_mute = (before.mute and not after.mute) or (before.self_mute and not after.self_mute)
        video   = not before.self_video and after.self_video
        no_video = before.self_video and not after.self_video
        stream  = not before.self_stream and after.self_stream
        no_stream = before.self_stream and not after.self_stream
        afk     = not before.afk and after.afk
        no_afk  = before.afk and not after.afk
        left    = before.channel != after.channel and after.channel is None
        join    = before.channel != after.channel and before.channel is None
        move    = before.channel != after.channel

        if deaf:
            msg = "has been deafened."
        elif no_deaf:
            msg = "has been undeafened."
        elif mute:
            msg = "has been muted."
        elif no_mute:
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
            msg = f"has moved from {before.channel} channel into {after.channel}."

        time = self.get_time()
        await self.get_log_channel().send(f"{time}: {member.name} {msg}")

async def setup(bot):
    await bot.add_cog(Surveillance(bot))

# TODO: Blacklist with Gsheets
# TODO: Helping method for stats observing in graphs

import random
import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from youtube_dl.utils import DownloadError

from cogs.music.player import MusicPlayer
from cogs.music.source import YTDLSource


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, interaction):
        """Retrieve the guild player, or generate one."""

        try:
            player = self.players[interaction.guild_id]
        except KeyError:
            player = MusicPlayer(interaction, self)
            self.players[interaction.guild_id] = player

        return player

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Leave the channel when all other members leave."""

        voice_state = member.guild.voice_client

        # Checking if the bot is connected to a channel and
        # if there is only 1 member connected to it (the bot itself)
        if voice_state is not None and len(voice_state.channel.members) == 1:
            await self.cleanup(member.guild)

    # Slash commands, the main command
    @app_commands.command(name='play')
    async def play_(self, interaction, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search, retrieves a song and streams it.

        Args:
            search: str [Required]
                The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """

        # making sure interaction timeout does not expire
        await interaction.response.send_message("...Looking for song(s)... wait...")

        # check if we're in channel, if not, join the one we are currently in
        vc = interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel
            await channel.connect()  # simplified cuz cannot invoke connect_

        # If download is False, source will be a list of entries which will be used to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        try:
            entries = await YTDLSource.create_source(interaction, search, loop=self.bot.loop, download=False)
        except DownloadError as e:
            await interaction.followup.send(e)
            return

        player = self.get_player(interaction)
        for entry in entries:
            source = {
                'webpage_url': entry['webpage_url'],
                'requester': interaction.user.display_name,
                'title': entry['title'],
            }
            player.queue.append(source)

        await player.dummy_queue.put(True)

    @app_commands.command(name='volume')
    async def change_volume(self, interaction, *, volume: int=None):
        """Change or see the volume of player in percentages.

        Args:
            volume: int
                The volume to set the player to in percentage. This must be between 1 and 100.
        """

        player = self.get_player(interaction)
        if volume is None:
            return await interaction.response.send_message(f"The volume is currently at **{int(player.volume*100)}%**.")
        elif not 0 < volume < 101:
            return await interaction.response.send_message("Please enter a value between 1 and 100.")

        vc = interaction.guild.voice_client
        if vc and vc.is_connected() and vc.source:
            vc.source.volume = volume / 100

        old_volume = player.volume * 100
        player.volume = volume / 100

        embed = discord.Embed(
            description=f'The volume has been set from **{int(old_volume)}%** to **{volume}%**',
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='join')
    async def connect_(self, interaction, *, channel: discord.VoiceChannel=None):
        """Connect to voice.
        This command also handles moving the bot to different channels.

        Args:
            channel: discord.VoiceChannel [Optional]
                The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
                will be made.
        """

        if not channel:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                return await interaction.response.send_message("No channel to join. Specify a valid channel or join one.")

        vc = interaction.guild.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return await interaction.response.send_message("I'm already in the channel.")
            try:
                await vc.move_to(channel)
                embed = discord.Embed(
                    description=f"Moved to channel: **{channel}**.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
            except asyncio.TimeoutError:
                await interaction.response.send_message(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
                embed = discord.Embed(
                    description=f"Connected to channel: **{channel}**.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
            except asyncio.TimeoutError:
                await interaction.response.send_message(f'Connecting to channel: <{channel}> timed out.')

    @app_commands.command(name='leave')
    async def leave_(self, interaction):
        """Stop the currently playing song, clears queue and disconnects from voice."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        await self.cleanup(interaction.guild)

        embed = discord.Embed(
            description=f'Left **{vc.channel.name}** channel.',
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # Invoked commands with voice check
    @app_commands.command(name="jump")
    async def jump_(self, interaction, index: int):
        """Jumps to specific track after currently playing song finishes."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")
        if 0 >= index or index > len(player.queue):
            return await interaction.response.send_message(f"Could not find a track at '{index}' index.")

        player.next_pointer = index-2

        embed = discord.Embed(
            description=f"Jumped to a {index}. song. It will be played after current one finishes.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='remove')
    async def remove_(self, interaction, index: int=None):
        """Removes specified or lastly added song from the queue."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")
        if index is None:
            index = len(player.queue)
        elif 0 >= index > len(player.queue):
            return await interaction.response.send_message(f"Could not find a track at '{index}' index.")

        s = player.queue[index-1]
        del player.queue[index-1]
        if index-1 <= player.next_pointer:
            player.next_pointer -= 1

        embed = discord.Embed(
            description=f"Removed {index}. song [{s['title']}]({s['webpage_url']}).",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='clear')
    async def clear_(self, interaction):
        """Deletes entire queue of songs."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")

        player.queue = [player.queue[player.current_pointer]]
        player.current_pointer = 0
        player.next_pointer = 0

        embed = discord.Embed(
            description="Queue has been cleared.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # Button commands
    async def pause_(self, interaction):
        """Pause the currently playing song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")
        if not vc.is_playing():
            return await interaction.response.send_message("I'm not currently playing anything.")
        elif vc.is_paused():
            return await interaction.response.send_message("The track is already paused.")

        vc.pause()

    async def resume_(self, interaction):
        """Resume the currently paused song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")
        if not vc.is_playing():
            return await interaction.response.send_message("I'm not currently playing anything.")
        elif not vc.is_paused():
            return await interaction.response.send_message("The track is already being played.")

        vc.resume()

    async def skip_(self, interaction):
        """Skips the song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")
        if not vc.is_playing():
            return await interaction.response.send_message("I'm not currently playing anything.")

        vc.stop()

    async def shuffle_(self, interaction):
        """Randomizes the position of tracks in queue."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")

        shuffled_remains = player.queue[player.current_pointer+1:]
        random.shuffle(shuffled_remains)

        player.queue = player.queue[:player.current_pointer+1] + shuffled_remains


    async def loop_queue_(self, interaction):
        """Loops the queue of tracks."""

        player = self.get_player(interaction)
        player.loop_queue = not player.loop_queue

    async def loop_track_(self, interaction):
        """Loops the currently playing track."""

        player = self.get_player(interaction)
        player.loop_track = not player.loop_track

async def setup(bot):
    await bot.add_cog(
        Music(bot),
        guilds=[discord.Object(
            id=os.environ.get("SERVER_ID")
        )]
    )

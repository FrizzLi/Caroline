import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import random
import asyncio
import itertools
import sys
import traceback
from async_timeout import timeout
from functools import partial
import youtube_dl
from youtube_dl import YoutubeDL
from typing import Any

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ytdl = YoutubeDL(ytdlopts)


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.duration = data.get('duration')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, interaction, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        entries = data['entries'] if 'entries' in data else [data]
        if 'entries' not in data or len(data['entries']) == 1:  # sometimes one song is treated as playlist with one entry
            data['title'] = entries[0]['title']
            data['webpage_url'] = entries[0]['webpage_url']

        description = f"Queued [{data['title']}]({data['webpage_url']}) [{interaction.user.mention}]"
        embed = discord.Embed(title="", description=description, color=discord.Color.green())
        await interaction.channel.last_message.delete()
        await interaction.followup.send(embed=embed)

        if download:
            source = ytdl.prepare_filename(entries)    # TODO: resolve [data]
        else:
            return entries

        return cls(discord.FFmpegPCMAudio(source), data=entries, requester=interaction.user)  # TODO: resolve [data] into data[0],, mention??

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""

        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'interaction', 'music', 'queue', 'dummy_queue', 'next', 'current', 'np', 'volume', 'current_pointer', 'next_pointer', 'loop_queue', 'loop_track')

    def __init__(self, interaction, music):
        self.bot = interaction.client  # interaction.client
        self._guild = interaction.guild  # interaction.guild
        self._channel = interaction.channel  # interaction.channel
        # self._cog = ctx.cog
        self.interaction = interaction
        self.music = music

        self.dummy_queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .02
        self.current = None

        self.queue = []  # type: Any
        self.current_pointer = 0
        self.next_pointer = -1
        self.loop_queue = False
        self.loop_track = False

        interaction.client.loop.create_task(self.player_loop())  # interaction.client

    async def player_loop(self):
        """Our main player loop."""

        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    await self.dummy_queue.get()

                    if not self.loop_track:
                        self.next_pointer += 1
                    if self.loop_queue and self.next_pointer >= len(self.queue):
                        self.next_pointer = 0
                    self.current_pointer = self.next_pointer
                    source = self.queue[self.current_pointer]

            except (asyncio.TimeoutError, IndexError):  # fix indexError...
                return self.destroy(self._guild)

            source_duration = source['duration']
            view_count = source['view_count']
            # thumbnail = source['thumbnail']

            # lets try without this?
            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                    source.duration = source_duration
                    source.view_count = view_count
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source
            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))

            view = MyView(self, source)

            if not self.np:
                self.np = await self._channel.send(embed=view.embed, view=view)  # maybe just view
            elif self.np.channel.last_message_id == self.np.id:
                self.np = await self.np.edit(embed=view.embed, view=view)
            else:
                await self.np.delete()
                self.np = await self._channel.send(embed=view.embed, view=view)

            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    # def set_queue_view(self):
    def destroy(self, guild):
        """Disconnect and cleanup the player."""

        return self.bot.loop.create_task(self.music.cleanup(guild))  # self.bot.loop.create_task(self.music.cleanup(guild))

    # TODO: think.. can be as a command too!
    def get_queue_info(self, source):
        """Display information about player and queue of songs."""

        # f"[{source.title}]({source.web_url})\n{self.get_queue_info(source)}"
        player = self
        track_list = []
        start = 1
        if player.current_pointer > 2 and len(player.queue) > 10:
            start = len(player.queue[player.current_pointer - 2 : player.current_pointer + 8])
            start += player.current_pointer - 11

        for index, queue_source in enumerate(
            player.queue[start - 1 : start + 9], start=start
        ):
            # current_pointer = "---> " if player.current_pointer + 1 == index else "     "
            audio_name = queue_source['title']  
            # TODO: DL (os.path.basename(track_path)[:-4])
            # audio_length = "95"  # MP3(track_path).info.length

            row = f"`{index}. `"
            if player.current_pointer + 1 > index:
                row += f"**{audio_name}**"
            elif player.current_pointer + 1 == index:
                row += f"**[{source.title}]({source.web_url})**"
            else:
                row += audio_name
            track_list.append(row)

        queue_view = "\n".join(track_list) + "\n"
        remains = len(player.queue[start + 9 :])
        # remains = f"{remains} remaining track(s)    " if remains else ""
        vol = f"{int(player.volume * 100)}%"
        loop_q = "✅" if player.loop_queue else "❌"
        loop_t = "✅" if player.loop_track else "❌"
        msg = f"{queue_view}\n\n{remains}\n{vol}\n{loop_q}\n{loop_t}\n"

        return queue_view, remains, vol, loop_q, loop_t

        # return msg


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

    # async def __local_check(self, ctx):
    #     """A local check which applies to all commands in this cog."""

    #     if not ctx.guild:
    #         raise commands.NoPrivateMessage
    #     return True

    # async def __error(self, ctx, error):
    #     """A local error handler for all errors arising from commands in this cog."""

    #     if isinstance(error, commands.NoPrivateMessage):
    #         try:
    #             return await ctx.send('This command can not be used in Private Messages.')
    #         except discord.HTTPException:
    #             pass
    #     elif isinstance(error, InvalidVoiceChannel):
    #         await ctx.send('Error connecting to Voice Channel. '
    #                        'Please make sure you are in a valid channel or provide me with one')

    #     print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
    #     traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, interaction):  # self, interaction
        """Retrieve the guild player, or generate one."""

        try:
            player = self.players[interaction.guild_id]  # interaction.guild_id
        except KeyError:
            player = MusicPlayer(interaction, self)  # interaction
            self.players[interaction.guild_id] = player  # interaction.guild_id

        return player

    def get_readable_duration(self, duration):
        """Get duration in hours, minutes and seconds."""

        seconds = int(duration % (24 * 3600))
        hour = int(seconds // 3600)
        seconds %= 3600
        minutes = int(seconds // 60)
        seconds %= 60

        duration = ""
        if hour:
            duration = f"{hour}h"
        if minutes:
            if hour:
                duration += " "
            duration += f"{minutes}m"
        if seconds:
            if hour or minutes:
                duration += " "
            duration += f"{seconds}s"

        return duration

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Leave the channel when all other members leave."""

        voice_state = member.guild.voice_client

        # Checking if the bot is connected to a channel and if there is only 1 member connected to it (the bot itself)
        if voice_state is not None and len(voice_state.channel.members) == 1:
            await self.cleanup(member.guild)

    # @app_commands.command(name='join')
    # async def connect_(self, interaction: discord.Interaction, *, channel: discord.VoiceChannel=None):
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
                channel = interaction.user.voice.channel  # interaction.user.voice.channel
            except AttributeError:
                await interaction.response.send_message("```No channel to join. Specify a valid channel or join one.```")
                # await interaction.response.send_message("```No channel to join. Specify a valid channel or join one.```")
                return 1

        vc = interaction.guild.voice_client  # interaction.guild.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return await interaction.response.send_message("```I'm already in the channel.```")  # await interaction.response.send_message("```I'm already in the channel.```")
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

        # await ctx.message.add_reaction('👌')  # DELETE....

    @app_commands.command(name='play')
    async def play_(self, interaction, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search, retrieves a song and streams it.

        Args:
            search: str [Required]
                The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """

        # async with ctx.typing():
        # a=2

        vc = interaction.guild.voice_client  # interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel  # interaction.user.voice.channel
            await channel.connect()
            # await self.connect_()
            # error = await ctx.invoke(self.connect_)
            # if error:
            #     return
        # else:
        #     vc = vc[0]
        a = 2
        player = self.get_player(interaction)  # interaction
        await interaction.response.send_message("```...Looking for song(s)...```")
        # If download is False, source will be a list of entries which will be used to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        entries = await YTDLSource.create_source(interaction, search, loop=self.bot.loop, download=False)
        for entry in entries:
            source = {
                'webpage_url': entry['webpage_url'],
                'requester': interaction.user.mention,
                'title': entry['title'],
                'duration': self.get_readable_duration(entry['duration']),
                'thumbnail': entry['thumbnail'],
                'view_count': entry['view_count']
            }
            player.queue.append(source)
            await player.dummy_queue.put(True)

        # await interaction.channel.last_message.delete()

    @commands.command(name='pause')
    async def pause_(self, interaction):
        """Pause the currently playing song."""

        vc = interaction.guild.voice_client  # interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("```I'm not currently playing anything.```")  # await interaction.response.send_message("```I'm not currently playing anything.```")
        elif vc.is_paused():
            return await interaction.response.send_message("```The track is already paused.```")  # await interaction.response.send_message("```The track is already paused.```")

        vc.pause()
        # await ctx.message.add_reaction('👌')  # DELETE

    @commands.command(name='resume')
    async def resume_(self, interaction):
        """Resume the currently paused song."""

        vc = interaction.guild.voice_client  # interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("```I'm not connected to a voice channel.```")  # await interaction.response.send_message
        elif not vc.is_paused():
            return await interaction.response.send_message("```The track is being played already.```")  # await interaction.response.send_message

        vc.resume()
        # await ctx.message.add_reaction('👌')

    @commands.command(name='skip')
    async def skip_(self, interaction):
        """Skips the song."""

        vc = interaction.guild.voice_client  # interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("```I'm not connected to a voice channel.```")  # await interaction.response.send_message

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        # await ctx.message.add_reaction('👌')  # DELETE

    @app_commands.command(name="jump")
    async def jump_(self, interaction, pos: int):
        """Jumps to specific track after currently played song finishes."""

        player = self.get_player(interaction)  # interaction
        if 0 < pos > len(player.queue):
            return await interaction.response.send_message(f"```Could not find a track at '{pos}' index.```")  # # await interaction.response.send_message

        player.next_pointer = pos-2
        # await ctx.message.add_reaction('👌')

    @app_commands.command(name='remove')
    async def remove_(self, interaction, pos: int=None):
        """Removes specified song from queue."""

        vc = interaction.guild.voice_client  # interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("```I'm not connected to a voice channel.```")

        player = self.get_player(interaction)
        if pos == None:
            pos = len(player.queue)
        elif 0 < pos > len(player.queue):
            return await interaction.response.send_message(f"```Could not find a track at '{pos}' index.```")

        s = player.queue[pos-1]
        del player.queue[pos-1]
        embed = discord.Embed(
            description=f"Removed [{s['title']}]({s['webpage_url']})",
            color=discord.Color.green()
        )
        # await ctx.message.add_reaction('👌')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='clear')
    async def clear_(self, interaction):
        """Deletes entire queue of upcoming songs."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("```I'm not connected to a voice channel.```")

        player = self.get_player(interaction)
        player.queue.clear()
        # await ctx.message.add_reaction('👌')

    # @commands.command(name='queue', aliases=['q', 'info'])
    # async def queue_info(self, ctx):
    #     """Display information about player and queue of songs."""

    #     player = self.get_player(ctx)
    #     track_list = []
    #     start = 1
    #     if player.current_pointer > 2 and len(player.queue) > 10:
    #         start = len(player.queue[player.current_pointer - 2 : player.current_pointer + 8])
    #         start += player.current_pointer - 11

    #     for index, source in enumerate(
    #         player.queue[start - 1 : start + 9], start=start
    #     ):
    #         current_pointer = "---> " if player.current_pointer + 1 == index else "     "
    #         audio_name = source['title']  
    #         # TODO: DL (os.path.basename(track_path)[:-4])
    #         # audio_length = "95"  # MP3(track_path).info.length

    #         row = f"{current_pointer}{index}.\t{source['duration']} {audio_name}"
    #         track_list.append(row)

    #     queue_view = "\n".join(track_list)
    #     remains = len(player.queue[start + 9 :])
    #     remains = f"{remains} remaining track(s)    " if remains else ""
    #     vol = f"volume: {int(player.volume * 100)}%"
    #     loop_q = f"loopqueue: {player.loop_queue}"
    #     loop_t = f"looptrack: {player.loop_track}"
    #     msg = f"```ml\n{queue_view}\n\n{remains}{vol}    {loop_q}    {loop_t}\n```"
    #     await ctx.send(msg)

    # @commands.command(name='np')
    # async def now_playing_(self, ctx):
    #     """Display information about the currently playing song."""

    #     vc = ctx.voice_client
    #     if not vc or not vc.is_connected():
    #         return await ctx.send("```I'm not connected to a voice channel.```")

    #     player = self.get_player(ctx)
    #     if not player.current:
    #         return await ctx.send("```I'm currently not playing anything.```")
        
    #     seconds = vc.source.duration % (24 * 3600) 
    #     hour = seconds // 3600
    #     seconds %= 3600
    #     minutes = seconds // 60
    #     seconds %= 60
    #     if hour > 0:
    #         duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
    #     else:
    #         duration = "%02dm %02ds" % (minutes, seconds)

    #     description = f"[{vc.source.title}]({vc.source.web_url})\nRequested by: {vc.source.requester}] | `{source['duration']}`"
    #     embed = discord.Embed(title="Now Playing 🎶", description=description, color=discord.Color.green())
    #     # embed.set_author(name=f"Now Playing 🎶")  # (icon_url=self.bot.user.avatar_url)
    #     await ctx.send(embed=embed)

    @app_commands.command(name='volume')
    async def change_volume(self, interaction, *, vol: int=None):
        """Change the player volume.

        Args:
            volume: int
                The volume to set the player to in percentage. This must be between 1 and 100.
        """

        player = self.get_player(interaction)
        if vol is None:
            return await interaction.response.send_message(f"The volume is currently at **{int(player.volume*100)}%**.")
        if not 0 < vol < 101:
            return await interaction.response.send_message("```Please enter a value between 1 and 100```")

        vc = interaction.guild.voice_client
        if vc and vc.is_connected() and vc.source:
            vc.source.volume = vol / 100

        old_vol = player.volume * 100
        player.volume = vol / 100
        await interaction.response.send_message(f'**`{interaction.user}`** set the volume from **{int(old_vol)}%** to **{vol}%**')

    @app_commands.command(name='leave')
    async def leave_(self, interaction):
        """Stop the currently playing song and disconnects from voice.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("```I'm not connected to a voice channel.```")

        # await ctx.message.add_reaction('👋')
        await self.cleanup(interaction.guild)  # OK???

    # @commands.command(name='stop')
    # async def stop_(self, ctx):
    #     """Stops current playing track and clears queue."""
    #     #voice = get(self.bot.voice_clients, guild=ctx.guild)
    #     vc = ctx.voice_client

    #     if not vc or not vc.is_connected():
    #         embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
    #         return await ctx.send(embed=embed)

    #     #self.loop_queue = False
    #     player = self.get_player(ctx)
    #     player.queue.clear()
    #     # await player.dummy_queue.task_done()
    #     vc.stop()

    @commands.command(name='shuffle')
    async def shuffle_(self, interaction):
        """Randomizes the position of tracks in queue."""

        player = self.get_player(interaction)
        shuffled_remains = player.queue[player.current_pointer + 1 :]

        random.shuffle(shuffled_remains)
        player.queue = player.queue[: player.current_pointer + 1] + shuffled_remains

        # await ctx.message.add_reaction('👌')

    @commands.command(name='loopq')
    async def loop_queue_(self, interaction):
        """Loops the whole queue of tracks."""

        player = self.get_player(interaction)
        player.loop_queue = not player.loop_queue

        # await ctx.message.add_reaction('👌')

    @commands.command(name='loopt')
    async def loop_track_(self, interaction):
        """Loops the currently playing track."""

        player = self.get_player(interaction)
        player.loop_track = not player.loop_track

        # await ctx.message.add_reaction('👌')


















    @commands.command()
    async def hell(self, ctx):
        button1 = MyButton()
        button2 = Button(emoji="⏸️")
        button3 = Button(label="Go to Google", url="https://google.com")

        async def button_callback(interaction):
            # await interaction.response.send_message("Hi!!", view=None) (gets removed)
            await interaction.response.edit_message("Hi!!")
            await interaction.response.edit_message(content="Hi!!")
            await interaction.followup.send("Hiiiii")
        button1.callback = button_callback
        # IF NEED TO RESPOND FAST - 13:55

        view = View(timeout=10)  # select menus, text input
        view.add_item(button1)
        view.add_item(button2)
        view.add_item(button3)
        # view.remove_item()
        embed = discord.Embed(title="sss", description="I'm not connected to a voice channel", color=discord.Color.green())
        await ctx.send(embed=embed, view=view)
        # await ctx.send("Hello!", view=view)






class MyButton(Button):
    def __init__(self):
        super().__init__(label="Play me!", style=discord.ButtonStyle.green, emoji="▶️")

    async def button_callback(self, interaction):  # MUST BE callback only
            # await interaction.response.send_message("Hi!!", view=None) (gets removed)
            await interaction.response.edit_message("Hi!!")
            await interaction.followup.send("Hiiiii")

class MyView(View):
    def __init__(self, music_player, source):
        super().__init__()
        self.music_player = music_player
        self.source = source
        self.embed = self.generate_embed_message()

    def generate_embed_message(self):
        tracks, remains, vol, loop_q, loop_t = self.get_queue_info()
        # embed.set_thumbnail(url=thumbnail)
        embed = discord.Embed(
            description=tracks,
            color=discord.Color.green()
        )
        embed.add_field(name='Remaining track(s)', value=remains)
        embed.add_field(name="Volume", value=vol)
        embed.add_field(name="Queue/Track Loop", value=f"{loop_q} / {loop_t}")
        embed.add_field(name='Requested by', value=self.source.requester)
        embed.add_field(name='Duration', value=self.source.duration, inline=True)
        embed.add_field(name='Views', value=f'{self.source.view_count:,}', inline=True)

        return embed

        # TODO: think.. can be as a command too!
    def get_queue_info(self):
        """Display information about player and queue of songs."""

        # f"[{source.title}]({source.web_url})\n{self.get_queue_info(source)}"
        player = self.music_player
        track_list = []
        start = 1
        if player.current_pointer > 2 and len(player.queue) > 10:
            start = len(player.queue[player.current_pointer - 2 : player.current_pointer + 8])
            start += player.current_pointer - 11

        for index, queue_source in enumerate(
            player.queue[start - 1 : start + 9], start=start
        ):
            # current_pointer = "---> " if player.current_pointer + 1 == index else "     "
            audio_name = queue_source['title']  
            # TODO: DL (os.path.basename(track_path)[:-4])
            # audio_length = "95"  # MP3(track_path).info.length

            row = f"`{index}. `"
            if player.current_pointer + 1 > index:
                row += f"**{audio_name}**"
            elif player.current_pointer + 1 == index:
                row += f"**[{self.source.title}]({self.source.web_url})**"
            else:
                row += audio_name
            track_list.append(row)

        tracks = "\n".join(track_list) + "\n"
        remains = len(player.queue[start + 9 :])
        # remains = f"{remains} remaining track(s)    " if remains else ""
        vol = f"{int(player.volume * 100)}%"
        loop_q = "✅" if player.loop_queue else "❌"
        loop_t = "✅" if player.loop_track else "❌"
        msg = f"{tracks}\n\n{remains}\n{vol}\n{loop_q}\n{loop_t}\n"

        return tracks, remains, vol, loop_q, loop_t

        # return msg
    # label="Click heere!", style=discord.ButtonStyle.green,
    # @discord.ui.button(emoji="⏮️")
    # async def prev_callback(self, button, interaction):
    #     # button.label = "WOW!"
    #     # button.disabled = True
    #     await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏸️")
    async def res_pau_callback(self, interaction, button):
        if button.emoji.name == "⏸️":
            error = await self.music_player.music.pause_(interaction)  # ctx.invoke(self.music_player.music.pause_)
            if not error:
                button.emoji.name = "▶️"
        elif button.emoji.name == "▶️":
            error = await self.music_player.music.resume_(interaction)  # .invoke(self.music_player.music.resume_)
            if not error:
                button.emoji.name = "⏸️"
        
        self.generate_embed_message()
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(emoji="⏭️")
    async def skip_callback(self, interaction, button):
        await self.music_player.music.skip_(interaction)  # .invoke(self.music_player.music.skip_)
        self.generate_embed_message()
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(emoji="🔁")
    async def loop_q_callback(self, interaction, button):
        await self.music_player.music.loop_queue_(interaction)  # .invoke(self.music_player.music.loop_queue_)
        embed = self.generate_embed_message()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(emoji="🔂")
    async def loop_t_callback(self, interaction, button):
        await self.music_player.music.loop_track_(interaction)  # ctx.invoke(self.music_player.music.loop_track_)
        embed = self.generate_embed_message()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(emoji="🎲")
    async def shuffle_callback(self, interaction, button):
        await self.music_player.music.shuffle_(interaction)  # ctx.invoke(self.music_player.music.shuffle_)
        embed = self.generate_embed_message()
        await interaction.response.edit_message(embed=embed, view=self)

    # async def on_timeout(self):
    #     await self.ctx.send("Timeout!")
    
    # # async def on_error(self, error, item, interaction):
    # #     await interaction.response.send_message(str(error))

    # # async def interaction_check(self, interaction) -> bool:
    # if interaction.user != self.ctx.author:
    #     await interaction.response.send_message("Hey! You cant use that!", ephemeral=True)
    #     return False
    # else:
    #     return True

async def setup(bot):
    await bot.add_cog(Music(bot), guilds=[discord.Object(id=553636358137053199)])

# clear, remove, jump, volume;;; leave/join [CMD!!!]
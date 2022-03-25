import discord
from discord.ext import commands
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
    'noplaylist': False,  # TODO: TryMe
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
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        entries = data['entries'] if 'entries' in data else [data]
        if 'entries' not in data or len(data['entries']) == 1:  # sometimes one song is treated as playlist with one entry
            data['title'] = entries[0]['title']
            data['webpage_url'] = entries[0]['webpage_url']

        embed = discord.Embed(title="", description=f"Queued [{data['title']}]({data['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.green())
        await ctx.send(embed=embed)

        if download:
            source = ytdl.prepare_filename(entries)    # TODO: resolve [data]
        else:
            return entries

        return cls(discord.FFmpegPCMAudio(source), data=entries, requester=ctx.author)  # TODO: resolve [data] into data[0]

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

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'dummy_queue', 'next', 'current', 'np', 'volume', 'current_pointer', 'next_pointer', 'loop_queue', 'loop_track')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.dummy_queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .05
        self.current = None

        self.queue = []  # type: Any
        self.current_pointer = 0
        self.next_pointer = -1
        self.loop_queue = False
        self.loop_track = False

        ctx.bot.loop.create_task(self.player_loop())

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

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            embed = discord.Embed(title="Now playing", description=f"[{source.title}]({source.web_url}) [{source.requester.mention}]", color=discord.Color.green())
            if self.np:
                await self.np.delete()
            self.np = await self._channel.send(embed=embed)
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    def destroy(self, guild):
        """Disconnect and cleanup the player."""

        return self.bot.loop.create_task(self._cog.cleanup(guild))


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

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""

        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""

        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""

        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(name='join')
    async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
        """Connect to voice.
        This command also handles moving the bot to different channels.

        Args:
            channel: discord.VoiceChannel [Optional]
                The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
                will be made.
        """

        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send("```No channel to join. Specify a valid channel or join one.```")

        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return await ctx.send("```I'm already in the channel.```")
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

        await ctx.message.add_reaction('👌')

    @commands.command(name='play', aliases=['p'])
    async def play_(self, ctx, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search, retrieves a song and streams it.

        Args:
            search: str [Required]
                The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """

        async with ctx.typing():

            vc = ctx.voice_client
            if not vc:
                await ctx.invoke(self.connect_)
            player = self.get_player(ctx)

            # If download is False, source will be a list of entries which will be used to regather the stream.
            # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
            entries = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)
            for entry in entries:
                source = {'webpage_url': entry['webpage_url'], 'requester': ctx.author, 'title': entry['title']}
                player.queue.append(source)
                await player.dummy_queue.put(True)

    @commands.command(name='pause')
    async def pause_(self, ctx):
        """Pause the currently playing song."""

        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("```I'm not currently playing anything.```")
        elif vc.is_paused():
            return await ctx.send("```The track is already paused.```")

        vc.pause()
        await ctx.message.add_reaction('👌')

    @commands.command(name='resume')
    async def resume_(self, ctx):
        """Resume the currently paused song."""

        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("```I'm not connected to a voice channel.```")
        elif not vc.is_paused():
            return await ctx.send("```The track is being played already.```")

        vc.resume()
        await ctx.message.add_reaction('👌')

    @commands.command(name='skip')
    async def skip_(self, ctx):
        """Skips the song."""

        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("```I'm not connected to a voice channel.```")

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.message.add_reaction('👌')

    @commands.command(name="jump")
    async def jump_(self, ctx, pos: int):
        """Jumps to specific track after currently played song."""

        player = self.get_player(ctx)
        if 0 < pos > len(player.queue):
            return await ctx.send(f"```Could not find a track at '{pos}' index.```")

        player.next_pointer = pos-1
        await ctx.message.add_reaction('👌')

    @commands.command(name='remove', aliases=['rm'])
    async def remove_(self, ctx, pos: int=None):
        """Removes specified song from queue."""

        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("```I'm not connected to a voice channel.```")

        player = self.get_player(ctx)
        if pos == None:
            pos = len(player.queue)
        elif 0 < pos > len(player.queue):
            return await ctx.send(f"```Could not find a track at '{pos}' index.```")

        s = player.queue[pos-1]
        del player.queue[pos-1]
        embed = discord.Embed(
            description=f"Removed [{s['title']}]({s['webpage_url']}) [{s['requester'].mention}]",
            color=discord.Color.green(),
        )
        await ctx.message.add_reaction('👌')
        await ctx.send(embed=embed)

    @commands.command(name='clear')
    async def clear_(self, ctx):
        """Deletes entire queue of upcoming songs."""

        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("```I'm not connected to a voice channel.```")

        player = self.get_player(ctx)
        player.queue.clear()
        await ctx.message.add_reaction('👌')

    @commands.command(name='queue', aliases=['q', 'info'])
    async def queue_info(self, ctx):
        """Display information about player and queue of songs."""

        vc = ctx.voice_client
        player = self.get_player(ctx)

        # # Grabs the songs in the queue...
        # upcoming = list(itertools.islice(player.queue, 0, int(len(player.queue))))
        # fmt = '\n'.join(f"`{(upcoming.index(_)) + 1}.` [{_['title']}]({_['webpage_url']}) | ` {duration} Requested by: {_['requester']}`\n" for _ in upcoming)
        # fmt = f"\n__Now Playing__:\n[{vc.source.title}]({vc.source.web_url}) | ` {duration} Requested by: {vc.source.requester}`\n\n__Up Next:__\n" + fmt + f"\n**{len(upcoming)} songs in queue**"
        # embed = discord.Embed(title=f'Queue for {ctx.guild.name}', description=fmt, color=discord.Color.green())
        # embed.set_footer(text=f"{ctx.author.display_name}")  # icon_url=ctx.author.avatar_url
        # await ctx.send(embed=embed)

        track_list = []
        start = 1
        if player.current_pointer > 2 and len(player.queue) > 10:
            start = len(player.queue[player.current_pointer - 2 : player.current_pointer + 8])
            start += player.current_pointer - 11

        for index, source in enumerate(
            player.queue[start - 1 : start + 9], start=start
        ):
            current_pointer = "---> " if player.current_pointer + 1 == index else "     "
            audio_name = source['title']  # TODO: DL (os.path.basename(track_path)[:-4])

            seconds = vc.source.duration % (24 * 3600)  # change
            hour = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60
            if hour > 0:
                duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
            else:
                duration = "%02dm %02ds" % (minutes, seconds)

            # audio_length = "95"  # MP3(track_path).info.length

            row = f"{str(current_pointer)}{str(index)}.\t{duration} {audio_name}"
            track_list.append(row)

        queue_view = "\n".join(track_list)
        remains = len(player.queue[start + 9 :])
        remains = f"{remains} remaining track(s)    " if remains else ""
        vol = f"volume: {str(int(player.volume * 100))}%"
        loop_q = f"loopqueue: {str(player.loop_queue)}"
        loop_t = f"looptrack: {str(player.loop_track)}"
        msg = f"ml\n{queue_view}\n\n{remains}{vol}    {loop_q}    {loop_t}\n"
        await ctx.send(f"```{msg}```")

    @commands.command(name='np')
    async def now_playing_(self, ctx):
        """Display information about the currently playing song."""

        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("```I'm not connected to a voice channel.```")

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send("```I'm currently not playing anything.```")
        
        seconds = vc.source.duration % (24 * 3600) 
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour > 0:
            duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
        else:
            duration = "%02dm %02ds" % (minutes, seconds)

        embed = discord.Embed(title="", description=f"[{vc.source.title}]({vc.source.web_url}) [{vc.source.requester.mention}] | `{duration}`", color=discord.Color.green())
        embed.set_author(name=f"Now Playing 🎶")  # (icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, ctx, *, vol: int=None):
        """Change the player volume.

        Args:
            volume: int
                The volume to set the player to in percentage. This must be between 1 and 100.
        """

        player = self.get_player(ctx)
        if vol is None:
            return await ctx.send(f"The volume is currently at **{int(player.volume*100)}%**.")
        if not 0 < vol < 101:
            return await ctx.send("```Please enter a value between 1 and 100```")

        vc = ctx.voice_client
        if vc and vc.is_connected() and vc.source:
            vc.source.volume = vol / 100

        old_vol = player.volume * 100
        player.volume = vol / 100
        await ctx.send(f'**`{ctx.author}`** set the volume from **{int(old_vol)}%** to **{vol}%**')

    @commands.command(name='leave')
    async def leave_(self, ctx):
        """Stop the currently playing song and disconnects from voice.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("```I'm not connected to a voice channel.```")

        await ctx.message.add_reaction('👋')
        await self.cleanup(ctx.guild)

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

    @commands.command()
    async def shuffle(self, ctx):
        """Randomizes the position of tracks in queue."""

        player = self.get_player(ctx)
        shuffled_remains = player.queue[player.current_pointer + 1 :]

        random.shuffle(shuffled_remains)
        player.queue = player.queue[: player.current_pointer + 1] + shuffled_remains

        await ctx.send(
            "```Position of remaning audio tracks in queue have been shuffled.```"
        )

    @commands.command()
    async def loopqueue(self, ctx):
        """Loops the whole queue of tracks."""

        player = self.get_player(ctx)
        if player.loop_queue:
            player.loop_queue = False
            await ctx.send("```queue looping is stopped.```")
        else:
            player.loop_queue = True
            await ctx.send("```Looping queue.```")

    @commands.command()
    async def looptrack(self, ctx):
        """Loops the currently playing track."""

        player = self.get_player(ctx)
        if player.loop_track:
            player.loop_track = False
            await ctx.send("Track looping is stopped.")
        else:
            player.loop_track = True
            await ctx.send("Looping current track.")

# class MyButton(Button):
#     def __init__(self):
#         super().__init__()

#     async def button_callback(self, interaction):
#             # await interaction.response.send_message("Hi!!", view=None) (gets removed)
#             await interaction.response.edit_message("Hi!!")

#             await interaction.followup.send("Hiiiii")

# import discord.ui import Button, View
# class MyView(View):
#     def __init__(self, ctx):
#         super().__init__(timeout=5)
#         self.ctx = ctx

#     @discord.ui.button(label="Click heere!", style=discord.ButtonStyle.green, emoji="▶️")
#     async def button_callback(self, button, interaction):
#         button.label = "WOW!"
#         button.disabled = True
#         await interaction.response.edit_message(view=self)

#     async def on_timeout(self):
#         await self.ctx.send("Timeout!")
    
#     # async def on_error(self, error, item, interaction):
#     #     await interaction.response.send_message(str(error))

#     # async def interaction_check(self, interaction) -> bool:
#     if interaction.user != self.ctx.author:
#         await interaction.response.send_message("Hey! You cant use that!", ephemeral=True)
#         return False
#     else:
#         return True

#     @commands.command()
#     async def hell(self, ctx):
#         button1 = MyButton(label="Play me!", style=discord.ButtonStyle.green, emoji="▶️")
#         button2 = Button(emoji="⏸️")
#         button3 = Button(label="Go to Google", url="https://google.com")

#         async def button_callback(interaction):
#             # await interaction.response.send_message("Hi!!", view=None) (gets removed)
#             await interaction.response.edit_message("Hi!!")

#             await interaction.followup.send("Hiiiii")
        
#         button1.callback = button_callback
#         view = View(timeout=10)  # select menus, text input
#         view.add_item(button1)
#         view.add_item(button2)
#         view.add_item(button3)
#         # view.remove_item()
#         await ctx.send("Hello!", view=view)

#         # ###await self.bot.wait_for("button_click")
#         # ###await commands.wait_for("button_click")
        
async def setup(bot):
    await bot.add_cog(Music(bot))

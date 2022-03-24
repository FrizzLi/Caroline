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

###
# from termcolor import colored
###

#     ydl_opts = {
#         "format": "bestaudio/best",
#         "quiet": True,
#         "postprocessors": [
#             {
#                 "key": "FFmpegExtractAudio",
#                 "preferredcodec": "mp3",
#                 "preferredquality": "192",
#             }
#         ],
#     }

#     ffmpeg_options = {"options": "-vn"}
# TODO: research props

# ffmpegopts = {
#     'before_options': '-nostdin',
#     'options': '-vn'
# }


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
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

        # TODO: how does channel var is translated from str to discord.VoiceChannel in code.. what does that pretyping?
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                embed = discord.Embed(title="", description="No channel to join. Please call `,join` from a voice channel.", color=discord.Color.green())
                await ctx.send(embed=embed)
                raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                await ctx.send("I'm already in the channel.")  # TODO: style
                return
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
            # await ctx.trigger_typing()

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
                # player.current_t.set()

    @commands.command(name='pause')
    async def pause_(self, ctx):
        """Pause the currently playing song."""

        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=discord.Color.green()) # TODO: style
            return await ctx.send(embed=embed)
        elif vc.is_paused():
            await ctx.send("The track is already paused.")  # TODO: style
            return

        vc.pause()
        await ctx.send("Paused ⏸️")

    @commands.command(name='resume')
    async def resume_(self, ctx):
        """Resume the currently paused song."""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green()) # TODO: styl
            return await ctx.send(embed=embed)
        elif not vc.is_paused():
            await ctx.send("The track is being played already.")  # TODO: style
            return

        vc.resume()
        await ctx.send("Resuming ⏯️")

    @commands.command(name='skip')
    async def skip_(self, ctx, index=None):
        """Skips the song."""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await ctx.send(embed=embed)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()  # remove this maybe

    @commands.command(aliases=["j"])
    async def jump(self, ctx, index):  # pretyping? does it throw error if i dont pass last arg. (index=None)
        """Jumps to specific track after currently played song."""
        # if index:
        #     self.jump_index = int(index)
        #     track = os.path.basename(self.queuer[self.jump_index - 1])
        #     msg = f"Jumping into {self.jump_index}. track ({track[:-4]})."
        # else:
        #     msg = "Skipping current track."
        # await ctx.send(msg)
        player = self.get_player(ctx)

        try:
            index_int = int(index)
            track = player.queue[index_int-1]
            player.next_pointer = index_int-1
        except ValueError as e:
            await ctx.send(f"Use numbers for index only. {e}")
        except TypeError as e:
            await ctx.send(f"You have to set index. {e}")
        except IndexError as e:
            await ctx.send(f"Queue does not have a song at selected index. {e}")

        await ctx.message.add_reaction('👌')

    @commands.command(name='remove', aliases=['rm'])
    async def remove_(self, ctx, pos : int=None):
        """Removes specified song from queue."""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        if pos == None:
            player.queue.pop()
        else:
            try:
                s = player.queue[pos-1]
                del player.queue[pos-1]
                embed = discord.Embed(title="", description=f"Removed [{s['title']}]({s['webpage_url']}) [{s['requester'].mention}]", color=discord.Color.green())
                await ctx.send(embed=embed)
            except:
                embed = discord.Embed(title="", description=f'Could not find a track for "{pos}"', color=discord.Color.green())
                await ctx.send(embed=embed)

    @commands.command(name='clear', aliases=['clr', 'cl'])
    async def clear_(self, ctx):
        """Deletes entire queue of upcoming songs."""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        player.queue.clear()
        await ctx.send('**Cleared**')

    @commands.command(name='queue', aliases=['q'])
    async def queue_info(self, ctx):
        """Display a queue of songs."""
        vc = ctx.voice_client

        # if not vc or not vc.is_connected():
        #     embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
        #     return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        # if not player.queue:
        #     embed = discord.Embed(title="", description="queue is empty", color=discord.Color.green())
        #     return await ctx.send(embed=embed)

        # seconds = vc.source.duration % (24 * 3600) 
        # hour = seconds // 3600
        # seconds %= 3600
        # minutes = seconds // 60
        # seconds %= 60
        # if hour > 0:
        #     duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
        # else:
        #     duration = "%02dm %02ds" % (minutes, seconds)

        # # Grabs the songs in the queue...
        # upcoming = list(itertools.islice(player.queue, 0, int(len(player.queue))))
        # fmt = '\n'.join(f"`{(upcoming.index(_)) + 1}.` [{_['title']}]({_['webpage_url']}) | ` {duration} Requested by: {_['requester']}`\n" for _ in upcoming)
        # fmt = f"\n__Now Playing__:\n[{vc.source.title}]({vc.source.web_url}) | ` {duration} Requested by: {vc.source.requester}`\n\n__Up Next:__\n" + fmt + f"\n**{len(upcoming)} songs in queue**"
        # embed = discord.Embed(title=f'Queue for {ctx.guild.name}', description=fmt, color=discord.Color.green())
        # embed.set_footer(text=f"{ctx.author.display_name}")  # icon_url=ctx.author.avatar_url

        # await ctx.send(embed=embed)

        # ###############
        track_list = []
        start = 1
        if player.current_pointer > 2 and len(player.queue) > 10:
            start = len(player.queue[player.current_pointer - 2 : player.current_pointer + 8])
            start += player.current_pointer - 11

        for index, source in enumerate(
            player.queue[start - 1 : start + 9], start=start
        ):
            current_pointer = "---> " if player.current_pointer + 1 == index else "     "
            audio_name = source['title'] # os.path.basename(track_path)[:-4]

            seconds = vc.source.duration % (24 * 3600) 
            hour = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60
            if hour > 0:
                duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
            else:
                duration = "%02dm %02ds" % (minutes, seconds)

            #
            # audio_length = "95"  # MP3(track_path).info.length
            # minutes = f"{str(int(audio_length) // 60)}m"
            # seconds = f"{str(int(audio_length) % 60)}s"
            # audio_length = f"({minutes}m {seconds}s)"
            #

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
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        if not player.current:
            embed = discord.Embed(title="", description="I am currently not playing anything", color=discord.Color.green())
            return await ctx.send(embed=embed)
        
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

    @commands.command(name='volume', aliases=['vol', 'v'])
    async def change_volume(self, ctx, *, vol: float=None):
        """Change the player volume.

        Args:
            volume: float or int [Required]
                The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I am not currently connected to voice", color=discord.Color.green())
            return await ctx.send(embed=embed)

        if not vol:
            embed = discord.Embed(title="", description=f"🔊 **{(vc.source.volume)*100}%**", color=discord.Color.green())
            return await ctx.send(embed=embed)

        if not 0 < vol < 101:
            embed = discord.Embed(title="", description="Please enter a value between 1 and 100", color=discord.Color.green())
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)  # TODO: what is this for?

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100  # TODO: ... ^
        embed = discord.Embed(title="", description=f'**`{ctx.author}`** set the volume to **{vol}%**', color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='leave', aliases=["l", "stop"])
    async def leave_(self, ctx):
        """Stop the currently playing song and disconnects from voice.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await ctx.send(embed=embed)

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
        return await ctx.send(
            "Position of remaning audio tracks in queue have been shuffled."
        )

    @commands.command()
    async def loopqueue(self, ctx):
        """Loops the whole queue of tracks."""
        player = self.get_player(ctx)
        if player.loop_queue:
            player.loop_queue = False
            await ctx.send("queue looping is stopped.")
        else:
            player.loop_queue = True
            await ctx.send("Looping queue.")

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

### TODO: research colorings

# def music_player_main(voice_channel,server):
#     vc = await voice_channel.connect()
#     while True:
#         clear()
#         print(colored("Channel: {}".format(voice_channel.name),menucolour))
#         print()
#         print(colored("1. Play YouTube Link.",menucolour))
#         print(colored("2. Pause Player",menucolour))
#         print(colored("3. Resume Player",menucolour))
#         print(colored("4. Stop Player",menucolour))
#         print(colored("5. Volume Adjustment",menucolour))
#         print(colored("6. Disconnect",menucolour))
#         try:
#             player_choice = await loop.run_in_executor(ThreadPoolExecutor(), inputselection,'Option: ')
#             if int(player_choice) == 1:
#                 clear()
#                 url = await loop.run_in_executor(ThreadPoolExecutor(), inputselection,'YouTube Link to play: ')
#                 try:
#                     if os.path.isfile('RTBFiles/ServerSmasher/file.mp3'):
#                         os.remove('RTBFiles/ServerSmasher/file.mp3')
#                         print ("Removed old .mp3.")
#                     with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#                         ydl.download([url])
#                     vc.play(discord.FFmpegPCMAudio('RTBFiles/ServerSmasher/file.mp3'))
#                     vc.source = discord.PCMVolumeTransformer(vc.source)
#                     vc.source.volume = 1.0
#                 except Exception as e:
#                     await loop.run_in_executor(ThreadPoolExecutor(), inputselection, str(e))
#             elif int(player_choice) == 2:
#                 vc.pause()
#             elif int(player_choice) == 3:
#                 vc.resume()
#             elif int(player_choice) == 4:
#                 vc.stop()
#             elif int(player_choice) == 5:
#                 clear()
#                 newvol = await loop.run_in_executor(ThreadPoolExecutor(), inputselection,'New Volume: ')
#                 try:
#                     vc.source.volume = float(int(newvol))
#                 except Exception as e:
#                     await loop.run_in_executor(ThreadPoolExecutor(), inputselection,e)
#             elif int(player_choice) == 6:
#                 await vc.disconnect(force=True)
#                 await music_player_channel_select(server)
#         except Exception as e:
#             continue

###

##########
# def play(self, ctx, *, query):
#     """Plays a file from the local filesystem"""

#     source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
#     ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

#     await ctx.send('Now playing: {}'.format(query))

async def setup(bot):
    await bot.add_cog(Music(bot))

































# import os
# import random
# import glob
# import discord
# import youtube_dl

# from discord.ext import commands
# from discord.utils import get, find
# from mutagen.mp3 import MP3


# class Voice(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     queuer = []  # type: Any
#     pointer = -1
#     loop_queue = False
#     loop_track = False
#     jump_index = 0
#     voluming = 0.1

#     def replaceChars(self, track):
#         track = track.replace('"', "'")
#         for char in "\\/:*?<>|":
#             track = track.replace(char, "_")

#         return track

#     def downloadAudio(self, query):
#         try:  # youtube source
#             with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:

#                 # get query title info (song/playlist name)
#                 if not query[0].startswith("https"):
#                     ydl.params["noplaylist"] = True
#                     extract_query = "ytsearch1:" + " ".join(query)
#                     info = ydl.extract_info(extract_query, download=False)
#                     title = info["entries"][0]["title"]
#                 else:
#                     ydl.params["noplaylist"] = False
#                     info = ydl.extract_info(query[0], download=False)
#                     title = info["title"]

#                 title = self.replaceChars(
#                     title
#                 )  # for special characters that cannot be saved

#                 # get local existing titles
#                 playlist = info["webpage_url_basename"] == "playlist"
#                 voice_dir = os.path.dirname(os.path.abspath(__file__))
#                 if playlist:
#                     dest = title
#                     audio_paths = voice_dir + "\\audio\\*"
#                 else:
#                     dest = "singles"
#                     audio_paths = voice_dir + "\\audio\\singles\\*.mp3"
#                 paths = glob.glob(audio_paths)
#                 titles = [os.path.basename(full_path) for full_path in paths]

#                 # download title if it doesnt exist
#                 if not (title + ".mp3") in titles:
#                     dl_path = f"{voice_dir}\\audio\\{dest}\\%(title)s.%(ext)s"
#                     ydl.params["outtmpl"] = dl_path
#                     ydl.extract_info(info["webpage_url"], download=True)

#         except Exception:  # TODO: spotify source
#             pass
#             """
#             url_str = " ".join(query)
#             list_type = 'album' if 'album' in url_str else ''
#             list_type = 'playlist' if 'playlist' in url_str else list_type
#             playlist = True if list_type else False
#             if list_type:
#                 # download list into text file and get its title
#                 os.system(f"spotdl --{list_type} {url_str}")
#                 paths = glob.glob("*")
#                 latest = max(paths, key=os.path.getctime)
#                 title = latest[:-4]

#                 # download if title doesnt exist
#                 paths = glob.glob("audio/*")
#                 dirs = [os.path.basename(path) for path in paths]
#                 if not title in dirs:
#                     path = f"audio\\{title}"
#                     q = f"spotdl --list={latest} -f {path} --overwrite skip"
#                     os.system(q)
#                 os.remove(latest)

#             else:
#                 # download the track
#                 name_format = '"' + "{artist} - {track_name}" + '"'
#                 path = f"audio\\DOWNLOAD"
#                 os.system(f"spotdl -ff {name_format} -f {path} -s \
#                     {url_str} --overwrite skip")

#                 # get name of the downloaded track
#                 paths = glob.glob(f"{path}/*.mp3")
#                 latest = max(paths, key=os.path.getctime)
#                 title = os.path.basename(latest)[:-4]
#             """

#         return title, playlist

#     def setQueue(self, query):
#         voice_dir = os.path.dirname(os.path.abspath(__file__))

#         # get audio path from local
#         if query[0][0] == "-":
#             title = query[0][1:]
#             audio_paths = glob.glob(f"{voice_dir}\\audio\\{title}\\*.mp3")
#             audio_paths.sort(key=lambda x: os.path.getctime(x))
#             try:
#                 index = int(query[1])
#                 audio_paths = [audio_paths[index - 1]]
#                 title = os.path.basename(audio_paths[0])[:-4]
#             except IndexError:
#                 pass

#         # download audio and get its path
#         elif query[0][0] == "+":
#             title, playlist = self.downloadAudio(query)
#             if playlist:
#                 audio_paths = f"{voice_dir}\\audio\\{title}\\*.mp3"
#             else:
#                 audio_paths = f"{voice_dir}\\audio\\*\\{title}.mp3"
#             audio_paths = glob.glob(audio_paths)
#             audio_paths.sort(key=lambda x: os.path.getctime(x))

#         # TODO: stream audio and get its URL
#         else:
#             with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
#                 # get query title info (song/playlist name)
#                 if not query[0].startswith("https"):
#                     ydl.params["noplaylist"] = True
#                     extract_query = "ytsearch1:" + " ".join(query)
#                     info = ydl.extract_info(extract_query, download=False)
#                     title = info["entries"][0]["title"]
#                 else:
#                     ydl.params["noplaylist"] = False
#                     info = ydl.extract_info(query[0], download=False)
#                     title = info["title"]
#                 if "entries" in info:
#                     audio_paths = [en["webpage_url"] for en in info["entries"]]
#                 else:
#                     audio_paths = [info["webpage_url"]]

#         # set queuer
#         title = self.replaceChars(
#             title
#         )  # for special characters that cannot be saved
#         audio_paths = glob.glob(f"{voice_dir}\\audio\\singles\\{title}.mp3")
#         for full_path in audio_paths:
#             self.queuer.append(full_path)

#         # self.queuer.append(title)
#         return title

# @commands.command(aliases=["p"], brief="Adds track to queue from ytb/spt.")
#     async def play(self, ctx, *query: str):

#         # queue playing loop
#         def check_queue():
#             if not self.loop_track:
#                 self.pointer += 1  # next
#             if self.jump_index:
#                 self.pointer = self.jump_index - 1  # jump
#             if self.loop_queue and len(self.queuer) < self.pointer + 1:
#                 self.pointer = 0  # repeat queue
#             if len(self.queuer) > self.pointer:
#                 track_path = self.queuer[self.pointer]  # play
#                 voice.play(
#                     discord.FFmpegPCMAudio(
#                         track_path, executable="C:/ffmpeg/ffmpeg.exe"
#                     ),
#                     after=lambda e: check_queue(),
#                 )
#                 voice.source = discord.PCMVolumeTransformer(voice.source)
#                 voice.source.volume = self.voluming
#             else:  # end
#                 self.pointer = -1
#                 self.queuer.clear()
#             self.jump_index = 0

#         # get audio and set the queue
#         async with ctx.typing():
#             title = self.setQueue(query)
#         await ctx.send(f"{title} has been added to the queue.")

#         # go to playing loop if there isnt song being played/paused
#         voice = get(self.bot.voice_clients, guild=ctx.guild)

#         # need the streaming tho!
#         if not voice.is_playing() and not voice.is_paused():
#             check_queue()







#     @commands.command(
#         aliases=["dl"], brief="DLs a track/playlist from ytb/spt URL. {URL}"
#     )
#     async def download(self, ctx, url):
#         if not url.startswith("https"):
#             return await ctx.send("Use web URL to download a song/playlist.")
#         async with ctx.typing():
#             title, playlist = self.downloadAudio((url,))
#             dir_name = title if playlist else "DOWNLOAD"
#         await ctx.send(
#             f'{title} has been downloaded to "{dir_name}" directory.'
#         )

#     @commands.command(
#         brief="Displays page of 10 tracks in directory. [dir_name] [page_num]"
#     )
#     async def view(self, ctx, dir_name="DOWNLOAD", page_num=1):
#         if not os.path.exists(f"audio/{dir_name}"):
#             return await ctx.send(f"{dir_name} directory does not exist.")

#         dirs = ""
#         if dir_name == "DOWNLOAD":
#             dirs = (
#                 "Available Directories: "
#                 + ", ".join(os.listdir("audio"))
#                 + "\n\n"
#             )
#         page_num = (page_num - 1) * 10
#         page_track = []
#         tracks = glob.glob(f"audio/{dir_name}/*.mp3")
#         tracks.sort(key=lambda x: os.path.getctime(x))
#         for index, track_path in enumerate(
#             tracks[page_num : page_num + 10], start=page_num + 1
#         ):
#             # TODO: This should be in function, its used elsewhere too!
#             audio_name = os.path.basename(track_path)[:-4]
#             audio_length = MP3(track_path).info.length
#             minutes = f"{str(int(audio_length // 60))}m"
#             seconds = f"{str(int(audio_length % 60))}s"
#             audio_length = f"({minutes}m {seconds}s)"
#             row = f"{str(index)}. {audio_length} {audio_name}"
#             page_track.append(row)

#         page_view = "\n".join(page_track)
#         remains = len(tracks[page_num + 10 :])
#         remains = f"{remains} remaining audio track(s)    " if remains else ""
#         msg = f"ml\n{dirs}Directory: {dir_name}\n{page_view}\n\n{remains}\n"
#         await ctx.send(f"```{msg}```")

#     """
#     @commands.command(aliases=['del'], brief="Deletes directory. {dir_name}")
#     async def zdelete(self, ctx, dir_name): # same user who created it
#         if not os.path.exists(f'audio/{dir_name}'):
#             return await ctx.send(f"{dir_name} directory does not exist.")

#         dir_tracks = os.listdir(f'audio/{dir_name}')
#         for track_path in self.queuer:
#             audio_name = os.path.basename(os.path.normpath(track_path))
#             if audio_name in dir_tracks:
#                 return await ctx.send(f"Track from {dir_name} is in queue!
#                 Clear the queue first.") # bug when two folders have same name

#         shutil.rmtree(f"audio/{dir_name}", ignore_errors=True)
#         await ctx.send(f"{dir_name} directory has been deleted.")
#     """

#     @queue.before_invoke
#     @pause.before_invoke
#     @resume.before_invoke
#     @stop.before_invoke
#     @jump.before_invoke
#     @volume.before_invoke
#     @shuffle.before_invoke
#     @loopqueue.before_invoke
#     @looptrack.before_invoke
#     async def ensure_voice(self, ctx):
#         voice = get(self.bot.voice_clients, guild=ctx.guild)
#         if not voice:
#             raise commands.CommandError("Not connected to voice channel.")
#         elif not self.queuer:
#             raise commands.CommandError("Queue is empty.")

#     @play.before_invoke
#     async def ensure_voice_play(self, ctx):
#         voice = get(self.bot.voice_clients, guild=ctx.guild)
#         user_voice = ctx.message.author.voice
#         if not voice and not user_voice:
#             raise commands.CommandError("No bot nor you is connected.")
#         elif not voice:
#             await user_voice.channel.connect()

#     # @zdelete.before_invoke
#     @view.before_invoke
#     @download.before_invoke
#     async def ensure_dldir(self, ctx):
#         if not os.path.exists("audio"):
#             os.mkdir("audio")
#             os.mkdir("audio/DOWNLOAD")
#         elif not os.path.exists("audio/DOWNLOAD"):
#             os.mkdir("audio/DOWNLOAD")

#     @commands.command(
#         brief="Brackets represent inputs. {} is mandatory, [] is optional.++"
#     )
#     async def HELP(self, ctx):
#         await ctx.send(
#             """```More facts about "play" command:
# Instead of URL you can put search query as well.
# The next two example commands have the same outcome:
#     play https://www.youtube.com/watch?v=89kTb73csYg
#     play forever young blackpink practice

# Can be also used to play local files.
# Example to play 2. track from directory named "DOWNLOAD":
#     play -DOWNLOAD 2
# ```"""
#         )


# def setup(bot):
#     bot.add_cog(Voice(bot))


# # ctx.voice_client vs get(self.bot.voice_clients, guild=ctx.guild)



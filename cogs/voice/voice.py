import random
import asyncio
import functools
import youtube_dl
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View  # Button, Select

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

ytdl = youtube_dl.YoutubeDL(ytdlopts)


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

        to_run = functools.partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        entries = data['entries'] if 'entries' in data else [data]
        if 'entries' not in data or len(data['entries']) == 1:  # TODO: sometimes one song is treated as playlist with one entry
            data['title'] = entries[0]['title']
            data['webpage_url'] = entries[0]['webpage_url']

        description = f"Queued [{data['title']}]({data['webpage_url']}) [{interaction.user.mention}]"
        embed = discord.Embed(title="", description=description, color=discord.Color.green())
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

        to_run = functools.partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('interaction', 'music', 'dummy_queue', 'next', 'np_msg', 'volume', 'current', 'queue', 'current_pointer', 'next_pointer', 'loop_queue', 'loop_track')

    def __init__(self, interaction, music):
        self.interaction = interaction
        self.music = music

        self.dummy_queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np_msg = None
        self.volume = .02
        self.current = None
        self.queue = []
        self.current_pointer = 0
        self.next_pointer = -1
        self.loop_queue = False
        self.loop_track = False

        interaction.client.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""

        await self.interaction.client.wait_until_ready()

        while not self.interaction.client.is_closed():
            self.next.clear()

            try:
                await self.dummy_queue.get()

                if not self.loop_track:
                    self.next_pointer += 1
                if self.loop_queue and self.next_pointer >= len(self.queue):
                    self.next_pointer = 0
                self.current_pointer = self.next_pointer
                source = self.queue[self.current_pointer]

            except (asyncio.TimeoutError, IndexError):  # TODO: fix indexError...
                return self.destroy(self.interaction.guild)

            source_duration = source['duration']
            view_count = source['view_count']
            # thumbnail = source['thumbnail']

            # TODO: try without this piece
            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.interaction.client.loop)
                    source.duration = source_duration
                    source.view_count = view_count
                except Exception as e:  # TODO: too general exception
                    await self.interaction.channel.send(
                        f'There was an error processing your song.\n```css\n[{e}]\n```'
                    )
                    continue

            source.volume = self.volume
            self.current = source
            self.interaction.guild.voice_client.play(source, after=lambda _: self.interaction.client.loop.call_soon_threadsafe(self.next.set))

            view = MyView(self, source)

            if not self.np_msg:
                self.np_msg = await self.interaction.channel.send(view.msg, view=view)  # TODO: try only view
            elif self.np_msg.channel.last_message_id == self.np_msg.id:
                self.np_msg = await self.np_msg.edit(view.msg, view=view)
            else:
                await self.np_msg.delete()
                self.np_msg = await self.interaction.channel.send(view.msg, view=view)

            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    def destroy(self, guild):
        """Disconnect and cleanup the player."""

        return self.interaction.client.loop.create_task(self.music.cleanup(guild))


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

    def _get_readable_duration(self, duration):
        """Get duration in hours, minutes and seconds."""

        m, s = divmod(duration, 60)
        h, m = divmod(m, 60)
        h = (f'{int(h)}h ' if h else '') + ' ' if m or s else ''
        m = (f'{int(m)}m ' if m else '') + ' ' if s else ''
        s = f'{int(s)}s' if s else ''
        duration = h + m + s

        return duration

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Leave the channel when all other members leave."""

        voice_state = member.guild.voice_client

        # Checking if the bot is connected to a channel and 
        # if there is only 1 member connected to it (the bot itself)
        if voice_state is not None and len(voice_state.channel.members) == 1:
            await self.cleanup(member.guild)

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
                    description=f"Moving to channel: <{channel}>.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
            except asyncio.TimeoutError:
                await interaction.response.send_message(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
                embed = discord.Embed(
                    description=f"Connecting to channel: <{channel}>.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
            except asyncio.TimeoutError:
                await interaction.response.send_message(f'Connecting to channel: <{channel}> timed out.')

    @app_commands.command(name='play')
    async def play_(self, interaction, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search, retrieves a song and streams it.

        Args:
            search: str [Required]
                The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """

        vc = interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel
            await channel.connect()  # TODO: use join function?

        player = self.get_player(interaction)
        await interaction.response.send_message("...Looking for song(s)... wait...")

        # If download is False, source will be a list of entries which will be used to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        entries = await YTDLSource.create_source(interaction, search, loop=self.bot.loop, download=False)
        for entry in entries:
            source = {
                'webpage_url': entry['webpage_url'],
                'requester': interaction.user.nick,  # mention for no old_msg
                'title': entry['title'],
                'duration': self._get_readable_duration(entry['duration']),
                'thumbnail': entry['thumbnail'],
                'view_count': entry['view_count']
            }
            player.queue.append(source)
            await player.dummy_queue.put(True)

    @app_commands.command(name="jump")
    async def jump_(self, interaction, pos: int):
        """Jumps to specific track after currently played song finishes."""

        player = self.get_player(interaction)
        if 0 < pos > len(player.queue):
            return await interaction.response.send_message(f"```Could not find a track at '{pos}' index.```")

        player.next_pointer = pos-2

        embed = discord.Embed(
            description=f"Jumped to a {pos}. song. It will be played after current one finishes.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='remove')
    async def remove_(self, interaction, pos: int=None):
        """Removes specified song from queue."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if pos is None:
            pos = len(player.queue)
        elif 0 < pos > len(player.queue):
            return await interaction.response.send_message(f"Could not find a track at '{pos}' index.")

        s = player.queue[pos-1]
        del player.queue[pos-1]

        embed = discord.Embed(
            description=f"Removed {pos}. song [{s['title']}]({s['webpage_url']}).",
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
        player.queue.clear()

        embed = discord.Embed(
            description="Queue has been cleared.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='volume')
    async def change_volume(self, interaction, *, vol: int=None):
        """Change the player volume.

        Args:
            volume: int
                The volume to set the player to in percentage. This must be between 1 and 100.
        """

        player = self.get_player(interaction)
        if vol is None:
            return await interaction.response.send_message(f"The volume is currently at **{player.volume*100}%**.")
        elif not 0 < vol < 101:
            return await interaction.response.send_message("Please enter a value between 1 and 100.")

        vc = interaction.guild.voice_client
        if vc and vc.is_connected() and vc.source:
            vc.source.volume = vol / 100

        old_vol = player.volume * 100
        player.volume = vol / 100

        embed = discord.Embed(
            description=f'The volume has been set from **{old_vol}%** to **{vol}%**',
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='leave')
    async def leave_(self, interaction):
        """Stop the currently playing song and disconnects from voice.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """

        # TODO: fix stop playing
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        await self.cleanup(interaction.guild)

        embed = discord.Embed(
            description=f'Left **{vc.channel.name}** channel.',
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @commands.command(name='pause')
    async def pause_(self, interaction):
        """Pause the currently playing song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("I'm not currently playing anything.")
        elif vc.is_paused():
            return await interaction.response.send_message("The track is already paused.")

        vc.pause()

    @commands.command(name='resume')
    async def resume_(self, interaction):
        """Resume the currently paused song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")
        elif not vc.is_paused():
            return await interaction.response.send_message("The track is being played already.")

        vc.resume()

    @commands.command(name='skip')
    async def skip_(self, interaction):
        """Skips the song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()

    @commands.command(name='loopq')
    async def loop_queue_(self, interaction):
        """Loops the queue of tracks."""

        player = self.get_player(interaction)
        player.loop_queue = not player.loop_queue

    @commands.command(name='loopt')
    async def loop_track_(self, interaction):
        """Loops the currently playing track."""

        player = self.get_player(interaction)
        player.loop_track = not player.loop_track

    @commands.command(name='shuffle')
    async def shuffle_(self, interaction):
        """Randomizes the position of tracks in queue."""

        player = self.get_player(interaction)

        shuffled_remains = player.queue[player.current_pointer+1:]
        random.shuffle(shuffled_remains)

        player.queue = player.queue[:player.current_pointer+1] + shuffled_remains


class MyView(View):
    def __init__(self, player, source):
        super().__init__()
        self.player = player
        self.np = source
        self.old_msg = True
        self.msg = self.generate_message()

    def generate_message(self):
        """Display information about player and queue of songs."""

        tracks, remains, volume, loop_q, loop_t = self._get_page_info()
        if self.old_msg:
            remains = f"{remains} remaining track(s)"
            vol = f"Volume: {volume}"
            loop_q = f"Loop Queue: {loop_q}"
            loop_t = f"Loop Track: {loop_t}"
            req = f"Requester: '{self.np.requester}'"
            dur = f"Duration: {self.np.duration}"
            views = f'Views: {self.np.view_count:,}'

            msg = (
                f"```ml\n{tracks}\n"
                f"{remains}     currently playing track:\n"
                f"{loop_q}              {req}\n"
                f"{loop_t}              {dur}\n"
                f"{vol}                   {views}```"
            )
        else:
            msg = discord.Embed(description=tracks, color=discord.Color.green())
            msg.add_field(name='Remaining track(s)', value=remains)
            msg.add_field(name="Volume", value=volume)
            msg.add_field(name="Queue/Track Loop", value=f"{loop_q} / {loop_t}")
            msg.add_field(name='Requested by', value=self.np.requester)
            msg.add_field(name='Duration', value=self.np.duration, inline=True)
            msg.add_field(name='Views', value=f'{self.np.view_count:,}', inline=True)

        return msg

    def _get_page_info(self):
        player = self.player
        first_row_index = self._get_first_row_index()
        track_list = self._get_track_list(first_row_index)

        tracks = "\n".join(track_list) + "\n"
        remains = len(player.queue[first_row_index+9:])
        volume = f"{int(player.volume * 100)}%"
        loop_q = "✅" if player.loop_queue else "❌"
        loop_t = "✅" if player.loop_track else "❌"

        return tracks, remains, volume, loop_q, loop_t

    def _get_first_row_index(self):
        queue = self.player.queue
        pointer = self.player.current_pointer

        s = 1
        if pointer > 2 and len(queue) > 10:
            remaining = len(queue[pointer: pointer + 8])
            s = remaining + pointer - 9

        return s

    def _get_track_list(self, s):
        queue = self.player.queue
        pointer = self.player.current_pointer

        track_list = []
        if self.old_msg:
            for row_index, track in enumerate(queue[s-1:s+9], start=s):
                row = "---> " if pointer + 1 == row_index else "     "
                row += f"{f'{row_index}. '[:4]}"
                row += track['title']
                track_list.append(row)
        else:
            for row_index, track in enumerate(queue[s-1:s+9], start=s):
                row = f"`{f'{row_index}. '[:3]}`"
                if pointer + 1 > row_index:
                    row += f"**{track['title']}**"
                elif pointer + 1 == row_index:
                    row += f"**[{self.np.title}]({self.np.web_url})**"
                else:
                    row += track['title']
                track_list.append(row)

        return track_list

    @discord.ui.button(emoji="⏸️")
    async def play_callback(self, interaction, button):
        if button.emoji.name == "⏸️":
            error = await self.player.music.pause_(interaction)
            if not error:
                button.emoji.name = "▶️"
        elif button.emoji.name == "▶️":
            error = await self.player.music.resume_(interaction)
            if not error:
                button.emoji.name = "⏸️"

        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️")
    async def skip_callback(self, interaction, button):
        await self.player.music.skip_(interaction)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="🔁")
    async def loop_q_callback(self, interaction, button):
        await self.player.music.loop_queue_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🔂")
    async def loop_t_callback(self, interaction, button):
        await self.player.music.loop_track_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🎲")
    async def shuffle_callback(self, interaction, button):
        await self.player.music.shuffle_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)


async def setup(bot):
    import json
    with open("config.json", "r") as f:
        gconfig = json.load(f)
    await bot.add_cog(Music(bot), guilds=[discord.Object(id=gconfig['server_id'])])

# MAYBE HELPFUL FUNCTIONS !!! (was already in src code)
# async def __local_check(self, ctx):
#     """A local check which applies to all commands in this cog."""

#     if not ctx.guild:
#         raise commands.NoPrivateMessage
#     return True
# import sys
# import traceback
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

# HELPFUL FOR MAKING BUTTONS/VIEW
# class MyButton(Button):
#     def __init__(self):
#         super().__init__(label="Play me!", style=discord.ButtonStyle.green, emoji="▶️")

#     async def button_callback(self, interaction):  # MUST BE callback only
#             # await interaction.response.send_message("Hi!!", view=None) (gets removed)
#             await interaction.response.edit_message("Hi!!")
#             await interaction.followup.send("Hiiiii")

#     @commands.command()
#     async def hell(self, ctx):
#         button1 = MyButton()
#         button2 = Button(emoji="⏸️")
#         button3 = Button(label="Go to Google", url="https://google.com")

#         async def button_callback(interaction):
#             # await interaction.response.send_message("Hi!!", view=None) (gets removed)
#             await interaction.response.edit_message("Hi!!")
#             await interaction.response.edit_message(content="Hi!!")
#             await interaction.followup.send("Hiiiii")
#         button1.callback = button_callback
#         # IF NEED TO RESPOND FAST - 13:55

#         view = View(timeout=10)  # select menus, text input
#         view.add_item(button1)
#         view.add_item(button2)
#         view.add_item(button3)
#         # view.remove_item()
#         embed = discord.Embed(title="sss", description="I'm not connected to a voice channel", color=discord.Color.green())
#         await ctx.send(embed=embed, view=view)
#         # await ctx.send("Hello!", view=view)

#     @commands.command()
#     async def hello(self, ctx):
#         button1 = MyButton()

# class MyView2(View):
# label="Click heere!", style=discord.ButtonStyle.green,
# @discord.ui.button(emoji="⏮️")
# async def prev_callback(self, button, interaction):
#     # button.label = "WOW!"
#     # button.disabled = True
#     await interaction.response.edit_message(view=self)

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

import json
import os
import re
from pathlib import Path

import discord
import gspread
import pandas as pd
import pytz
import youtube_dl
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from pytube import Playlist

from cogs.music.player import MusicPlayer
from cogs.music.player_view import SearchView, get_readable_duration
from cogs.music.source import YTDLSource, ytdl


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.timezone = ""

    async def cleanup(self, guild):
        """Deletes guild player if one exists.

        Args:
            guild (discord.guild.Guild): discord server the bot is currently in
        """

        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, interaction):
        """Retrieves guild player, or generates one if one does not exist.

        Args:
            interaction (discord.interaction.Interaction): slash cmd context

        Returns:
            cogs.music.player.MusicPlayer: music player
        """

        try:
            player = self.players[interaction.guild_id]
        except KeyError:
            player = MusicPlayer(interaction, self)
            self.players[interaction.guild_id] = player

        return player

    def get_ytb_data_from_url(self, inquiry):
        """Gets youtube data from inquiry.

        Args:
            inquiry (str): search term or URL link to the youtube video

        Returns:
            Tuple[str, str, str]: duration, views, categories
        """

        # NOTE: doing the mistake to go through helping methods first, without knowing whats happening outside, start with outside stuff
        data = ytdl.extract_info(url=inquiry, download=False)

        # YoutubeTab = playlist URL (has no duration, views nor categories data)
        if data["extractor_key"] == "YoutubeTab":
            return "", "", ""

        # YoutubeSearch = search term (founds more songs, we want first one)
        if data["extractor_key"] == "YoutubeSearch":
            data["duration"] = data["entries"][0]["duration"]
            data["view_count"] = data["entries"][0]["view_count"]
            data["categories"] = data["entries"][0]["categories"]
        
        duration = get_readable_duration(data["duration"])
        views = f"{data['view_count']:,}"
        categories = ", ".join(data["categories"])

        return duration, views, categories

    async def get_ytb_data_from_embed_req(self, ctx, msg):
        """Gets youtube data from embedded message.

        Args:
            ctx (discord.ext.commands.context.Context): context (old commands)
            msg (discord.message.Message): discord's message in the chatroom

        Returns:
            Tuple[str, str, str, str]: datetime, author_name, title, webpage_url
        """

        # pattern: Queued <song_name> [@<requester>]
        matching_expr = r"Queued \[(.+?)\]\((.+?)\) \[<@!?(\d+)>]"
        msg_descr = msg.embeds[0].description
        result = re.match(matching_expr, msg_descr)
        if result:  # TODO: why is there IF?
            title = result[1].replace('"', "'")
            webpage_url = result[2].replace('"', "'")
            author_id = result[3]
            author_name = await ctx.guild.fetch_member(author_id).name

        tz_aware_date = msg.created_at.astimezone(pytz.timezone(self.timezone))
        datetime = tz_aware_date.strftime("%Y-%m-%d %#H:%M:%S")

        rec = datetime, author_name, title, webpage_url

        return rec

    # Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        """Executes when the cog is loaded and inits timezone string."""

        with open("config.json", encoding="utf-8") as file:
            self.timezone = json.load(file)["timezone"]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Leave the channel when all the other members leave.

        Args:
            member (discord.member.Member): the bot
            before (discord.member.VoiceState): state before certain
                (anyone's) action [unused]
            after (discord.member.VoiceState): state after certain
                (anyone's) action [unused]
        """

        voice_state = member.guild.voice_client
        if not voice_state:
            return
        members_amount = len(voice_state.channel.members)

        # Checks if the bot is connected in the voice channel and
        # whether theres only 1 member connected to it (the bot itself)
        if voice_state is not None and members_amount == 1:
            await self.cleanup(member.guild)

    # General commands (with no slash)
    @commands.command()
    async def history(self, ctx, limit: int = 1000):
        """Saves history of songs into Google Sheets.

        Args:
            ctx (discord.ext.commands.context.Context): context (old commands)
            limit (int, optional): amount of messages to read.
                Defaults to 1000.
        """

        table_rows = []
        i = 0
        async for msg in ctx.channel.history(limit=limit):
            if msg.author.bot:
                if msg.content.startswith("___"):
                    break

                i += 1
                if msg.embeds and msg.embeds[0].description.startswith("Que"):
                    rec = self.get_ytb_data_from_embed_req(ctx, msg)
                    table_rows.append(rec)
                    print(f"{i}. (new) downloaded: {rec}")


        # TODO deal with all loadings in other files in the same time
        # save to gsheets
        credentials_dict_string = os.environ["GOOGLE_CREDENTIALS"]
        credentials_dict = json.loads(credentials_dict_string)
        g_credentials = gspread.service_account_from_dict(credentials_dict)
        g_sheet = g_credentials.open("Discord Music Log")

        # cr: g_sheet.add_worksheet("Commands Log", df.shape[0], df.shape[1])
        g_work_sheet = g_sheet.worksheet("Commands Log")
        df = pd.DataFrame(table_rows, index=None)
        wks_formatted_rows = df.values.tolist()
        g_work_sheet.append_rows(
            wks_formatted_rows, value_input_option="USER_ENTERED"
        )

        await ctx.send("___Messages saved up to this point.___")

    @commands.command(aliases=["dl"])
    async def download(self, ctx, link):
        plist = Playlist(ctx.current_argument)
        src_dir = Path(__file__).parents[0]
        playlist_dir = Path(f"{src_dir}/downloaded/{plist.title}")

        for video in plist.videos:
            print(video.title)
            audio = video.streams.get_audio_only()
            audio.download(playlist_dir)
            # audio1 = video.streams.filter(only_audio=True)
            # audio2 = video.streams.get_highest_resolution()
            # video.streams.first().download()

        await ctx.send(f"'{plist.title}' playlist has been downloaded!")

    @commands.command()
    async def create_stats(self, ctx):
        """Saves history of songs into Google Sheets."""

        # get pandas format
        credentials_dict_string = os.environ["GOOGLE_CREDENTIALS"]
        credentials_dict = json.loads(credentials_dict_string)
        g_credendials = gspread.service_account_from_dict(credentials_dict)
        g_sheet = g_credendials.open("Discord Music Log")
        cmd_wks = g_sheet.worksheet("Commands Log")
        cmd_df = pd.DataFrame(cmd_wks.get_all_records())
        cmd_df["Date"] = pd.to_datetime(cmd_df["Date"])
        now = pd.Timestamp.now()

        # preparation
        name_offset_dict = {
            "Track Log (Lifetime)": False,
            "Track Log (Year)": pd.DateOffset(years=1),
            "Track Log (3 Months)": pd.DateOffset(months=3),
            "Track Log (Month)": pd.DateOffset(months=1),
            "Track Log (Week)": pd.DateOffset(weeks=1),
        }

        for sheet_name, offset in name_offset_dict.items():
            print(sheet_name, "-----BEGINS-----")
            track_wks = g_sheet.worksheet(sheet_name)
            track_df = pd.DataFrame(track_wks.get_all_records())
            if track_df.empty:
                track_df = pd.DataFrame(
                    columns=[
                        "First time requested",
                        "Last time requested",
                        "Requests",
                        "Title",
                        "URL",
                        "Duration",
                        "Views",
                        "Categories",
                    ]
                )

            # filter months
            if offset:
                timestamp = now - offset
                filter_ = cmd_df["Date"] >= timestamp
                filtered_cmd_df = cmd_df[filter_]
            else:
                filtered_cmd_df = cmd_df

            # groupby titles
            grouped_cmd_df = filtered_cmd_df.groupby(["URL", "Title"])["Date"]
            function_list = [
                ("First time requested", "min"),
                ("Last time requested", "max"),
                ("Requests", "count"),
            ]
            grouped_cmd_df = grouped_cmd_df.agg(function_list).reset_index()

            # merge with track_df, rearrange, clean data
            track_df = track_df.drop(
                labels=[
                    "First time requested",
                    "Last time requested",
                    "Requests",
                    "Title",
                ],
                axis=1,
            )
            merged_df = pd.merge(
                grouped_cmd_df, track_df, on="URL", how="left"
            )
            merged_df = merged_df[
                [
                    "First time requested",
                    "Last time requested",
                    "Requests",
                    "Title",
                    "URL",
                    "Duration",
                    "Views",
                    "Categories",
                ]
            ]
            merged_df["First time requested"] = merged_df[
                "First time requested"
            ].astype(str)
            merged_df["Last time requested"] = merged_df[
                "Last time requested"
            ].astype(str)
            merged_df = merged_df.fillna(0)
            merged_df = merged_df.sort_values(by="Requests", ascending=False)

            # fill missing cells
            for i, row in enumerate(merged_df.itertuples(), 1):
                ytb_stats = row.Duration, row.Views, row.Categories
                if not all(ytb_stats):
                    try:
                        (
                            duration,
                            views,
                            categories,
                        ) = self.get_ytb_data_from_url(row.URL)
                    except Exception as err:
                        print(f"{i}. error: {err}. (row: {row})")
                        continue

                    merged_df.at[row.Index, "Duration"] = duration.replace(
                        ":", "︰"
                    )
                    merged_df.at[row.Index, "Views"] = views
                    merged_df.at[row.Index, "Categories"] = categories
                    msg = f"({duration}, {views}, {categories}) -- {row.Title}"
                    print(f"Updated {i} row. {msg}")

            # save to gsheets
            listed_table_result = [merged_df.columns.values.tolist()]  # header
            listed_table_result += merged_df.values.tolist()

            track_wks.update(
                listed_table_result, value_input_option="USER_ENTERED"
            )  # value_input_option='USER_ENTERED' / 'RAW'

        await ctx.send("___Stats updated up to this point.___")

    # Slash commands, the main command
    @app_commands.command(name="play")
    async def _play(self, interaction, *, search: str):
        """Request a song and add it to the queue.

        This command attempts to join valid voice channel if the bot is not
        already in one. Uses YTDL to automatically search, retrieves a song
        and streams it.

        Args:
            search: str [Required]
                The song to search and retrieve using YTDL.
                This could be a simple search, an ID or URL.
        """

        await self.play(interaction, search)

    async def play(self, interaction, search):

        # music = controller
        # player_view = view in discord
        # player = controls the flow of songs being played
        # source = a song

        # making sure interaction timeout does not expire
        await interaction.response.send_message(
            "...Looking for song(s)... wait..."
        )

        # check if we're in channel, if not, join the one we are currently in
        vc = interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel
            await channel.connect()  # simplified cuz cannot invoke connect f.

        # getting source entries ready to be played
        try:
            entries = await YTDLSource.create_source(
                interaction, search, loop=self.bot.loop
            )
        except youtube_dl.utils.DownloadError as err:
            await interaction.followup.send(err)
            return

        # getting the player, if it doesnt play anything, send signal to play
        player = self.get_player(interaction)
        send_signal = (
            True if player.next_pointer >= len(player.queue) else False
        )
        for entry in entries:
            source = {
                "webpage_url": entry["webpage_url"],
                "requester": interaction.user.name,
                "title": entry["title"],
            }
            player.queue.append(source)

        if send_signal:
            print("SIGNAL FROM MUSIC.PY")
            player.next.set()
            print("SIGNALED FROM MUSIC.PY")
        elif player.np_msg:
            player.view.update_msg()
            await player.update_player_status_message()

    # TODO: Update view?
    @app_commands.command(name="volume")
    async def change_volume(self, interaction, *, volume: int = None):
        """Change or see the volume of player in percentages.

        Args:
            volume: int
                The volume to set the player to in percentage. (1-100)
        """

        player = self.get_player(interaction)
        if volume is None:
            msg = f"The volume is currently at **{int(player.volume*100)}%**."
            return await interaction.response.send_message(msg)
        elif not 0 < volume < 101:
            msg = "Please enter a value between 1 and 100."
            return await interaction.response.send_message(msg)

        vc = interaction.guild.voice_client
        if vc and vc.is_connected() and vc.source:
            vc.source.volume = volume / 100

        old_volume = player.volume * 100
        player.volume = volume / 100

        descr = "The volume has been set from "
        descr += f"**{int(old_volume)}%** to **{volume}%**"
        embed = discord.Embed(
            description=descr,
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join")
    async def connect(
        self, interaction, *, channel: discord.VoiceChannel = None
    ):
        """Connect to voice.
        This command also handles moving the bot to different channels.

        Args:
            channel: discord.VoiceChannel [Optional]
                The channel to connect to. If a channel is not specified,
                an attempt to join the voice channel you are in will be made.
        """

        if channel is None:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                msg = "No channel to join. Specify valid channel or join one."
                return await interaction.response.send_message(msg)

        vc = interaction.guild.voice_client
        if vc:
            if vc.channel.id == channel.id:
                msg = "I'm already in the channel."
                return await interaction.response.send_message(msg)
            try:
                await vc.move_to(channel)
                embed = discord.Embed(
                    description=f"Moved to channel: **{channel}**.",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            except TimeoutError:
                msg = f"Moving to channel: <{channel}> timed out."
                await interaction.response.send_message(msg)
        else:
            try:
                await channel.connect()
                embed = discord.Embed(
                    description=f"Connected to channel: **{channel}**.",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            except TimeoutError:
                msg = f"Connecting to channel: <{channel}> timed out."
                await interaction.response.send_message(msg)

    @app_commands.command()
    async def leave(self, interaction):
        """Stop the currently playing song, clears queue and disconnects from
        voice.
        """

        voice = get(self.bot.voice_clients, guild=interaction.guild)
        # vc = interaction.guild.voice_client
        if not voice:
            msg = "I'm not connected to a voice channel."
            return await interaction.response.send_message(msg)

        await self.cleanup(interaction.guild)

        embed = discord.Embed(
            description=f"Left **{voice.channel.name}** channel.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    # Invoked commands with voice check
    @app_commands.command()
    async def jump(self, interaction, index: int):
        """Jumps to specific track after currently playing song finishes."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            msg = "I'm not connected to a voice channel."
            return await interaction.response.send_message(msg)

        player = self.get_player(interaction)
        if not player.queue:
            msg = "There is no queue."
            return await interaction.response.send_message(msg)
        if 0 >= index or index > len(player.queue):
            msg = f"Could not find a track at '{index}' index."
            return await interaction.response.send_message(msg)

        player.next_pointer = index - 2

        descr = f"Jumped to a {index}. song. "
        descr += "It will be played after current one finishes."
        embed = discord.Embed(
            description=descr,
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def remove(self, interaction, index: int = None):
        """Removes specified or lastly added song from the queue."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            msg = "I'm not connected to a voice channel."
            return await interaction.response.send_message(msg)

        player = self.get_player(interaction)
        if not player.queue:
            msg = "There is no queue."
            return await interaction.response.send_message(msg)
        if index is None:
            index = len(player.queue)
        elif 0 >= index > len(player.queue):
            msg = f"Could not find a track at '{index}' index."
            return await interaction.response.send_message(msg)

        s = player.queue[index - 1]
        del player.queue[index - 1]
        if index - 1 <= player.next_pointer:
            player.next_pointer -= 1
        if index - 1 <= player.current_pointer:
            player.current_pointer -= 1

        descr = f"Removed {index}. song [{s['title']}]({s['webpage_url']})."
        embed = discord.Embed(
            description=descr,
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def clear(self, interaction):
        """Deletes entire queue of songs."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            msg = "I'm not connected to a voice channel."
            return await interaction.response.send_message(msg)

        player = self.get_player(interaction)
        if not player.queue:
            msg = "There is no queue."
            return await interaction.response.send_message(msg)

        player.queue.clear()
        player.current_pointer = 0
        player.next_pointer = -1
        vc.stop()

        embed = discord.Embed(
            description="Queue has been cleared.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    # duration view does not work according to it!
    @app_commands.command()
    async def seek(self, interaction, second: int = 0):
        """Goes to a specific timestamp of currently played track."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            msg = "I'm not connected to a voice channel."
            return await interaction.response.send_message(msg)

        player = self.get_player(interaction)
        if vc.is_paused() or not vc.is_playing():
            msg = "There is no song being played."
            return await interaction.response.send_message(msg)

        player.timestamp = second
        player.next_pointer -= 1
        vc.stop()

        embed = discord.Embed(
            description="Track has been seeked.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def search(self, interaction, search: str):
        """Searches 10 entries from query."""

        # making sure interaction timeout does not expire
        await interaction.response.send_message(
            "...Looking for song(s)... wait..."
        )

        try:
            entries = await YTDLSource.search_source(
                search, loop=self.bot.loop
            )
        except youtube_dl.utils.DownloadError as err:
            await interaction.followup.send(err)
            return

        # load it into view
        player = self.get_player(interaction)
        view = SearchView(player, entries)
        await interaction.channel.send(view.msg, view=view)

    @app_commands.command(name="pick_from_playlist")
    async def pick_from_playlist(self, interaction, search: str):
        """Display all songs from a playlist to pick from."""

        # making sure interaction timeout does not expire
        await interaction.response.send_message(
            "...Looking for song(s)... wait..."
        )

        # get entries
        try:
            entries = await YTDLSource.create_source(
                interaction, search, loop=self.bot.loop, playlist=True
            )
        except youtube_dl.utils.DownloadError as err:
            await interaction.followup.send(err)
            return

        # load it into view
        player = self.get_player(interaction)
        view = SearchView(player, entries)
        await interaction.channel.send(view.msg, view=view)

    # Button commands
    async def pause(self, interaction):
        """Pause the currently playing song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return
        elif vc.is_paused():
            return

        vc.pause()

    async def resume(self, interaction):
        """Resume the currently paused song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return
        elif not vc.is_paused():
            return

        vc.resume()

    async def skip(self, interaction):
        """Skips the song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return
        if not vc.is_playing() and not vc.is_paused():
            return

        vc.stop()

    async def shuffle(self, interaction):
        player = self.get_player(interaction)
        player.shuffle()

    async def loop_queue(self, interaction):
        player = self.get_player(interaction)
        player.toggle_loop_queue()

    async def loop_track(self, interaction):
        player = self.get_player(interaction)
        player.toggle_loop_track()


async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        Music(bot), guilds=[discord.Object(id=os.environ["SERVER_ID"])]
    )

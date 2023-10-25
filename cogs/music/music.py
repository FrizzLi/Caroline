import asyncio
import functools
import json
import os
import re

import discord
import pandas as pd
import pytz
import youtube_dl
from discord import app_commands
from discord.ext import commands

import utils
from cogs.music.player import MusicPlayer
from cogs.music.player_view import SearchView, get_readable_duration
from cogs.music.source import YTDLSource, ytdl


def to_thread(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, wrapped)

    return wrapper


class Music(commands.Cog):
    # music = controller
    # player_view = view in discord
    # player = controls the flow of songs being played
    # source = a song

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.timezone = ""

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

    @to_thread
    def get_ytb_data_from_url(self, inquiry):
        """Gets youtube data from inquiry.

        Args:
            inquiry (str): search term or URL link to the youtube video

        Returns:
            Tuple[str, str, str]: duration, views, categories
        """

        data = ytdl.extract_info(url=inquiry, download=False)

        # Video/Stream unavailable (uploader/video does not exist, private etc)
        if not data:
            return "", "", ""

        # YoutubeTab = playlist URL (has no duration, views, categories)
        if data["extractor_key"] == "YoutubeTab":
            return "", "", ""

        # YoutubeSearch = search term (found more songs, we want first one)
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

        title = result[1].replace('"', "'")
        webpage_url = result[2].replace('"', "'")
        author_id = result[3]
        try:
            author = await ctx.guild.fetch_member(author_id)
            author_name = author.name
        except discord.errors.NotFound:
            author_name = "UNKNOWN"

        tz_aware_date = msg.created_at.astimezone(pytz.timezone(self.timezone))
        datetime = tz_aware_date.strftime("%Y-%m-%d %#H:%M:%S")

        rec = datetime, author_name, title, webpage_url

        return rec

    # Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        """Executes when the cog is loaded, it initializes timezone.

        This could have been initialized in __init__ method, but to make it
        consistent with all cogs, on_ready is being used for config loading.
        Surveillance module needs to load it there."""

        with open("config.json", encoding="utf-8") as file:
            self.timezone = json.load(file)["timezone"]

    # General commands (with no slash)  [!beware to have enough rows!!!]
    @commands.command()
    async def history(self, ctx, limit: int = 1000):
        """Saves song request commands information into Google Sheets.

        Args:
            ctx (discord.ext.commands.context.Context): context (old commands)
            limit (int, optional): amount of messages to read.
                Defaults to 1000.
        """

        ws_records = []
        i = 0
        async for msg in ctx.channel.history(limit=limit):
            if msg.author.bot and msg.author.name in ("GLaDOS", "Caroline"):
                if msg.content.startswith("___"):
                    print("Found saving breakpoint.")
                    break

                i += 1
                if msg.embeds and msg.embeds[0].description:
                    if msg.embeds[0].description.startswith("Queued ["):
                        rec = await self.get_ytb_data_from_embed_req(ctx, msg)
                        ws_records.append(rec)
                        print(f"{i}. (new) downloaded: {rec}")

        wss, _ = utils.get_worksheets("Discord Music Log", ("Commands Log",))
        log_ws = wss[0]
        log_ws.append_rows(ws_records, value_input_option="USER_ENTERED")

        await ctx.send("___Messages saved up to this point.___")

    # ! TODO commit till this line!
    @commands.command()
    async def create_stats(self, ctx):
        """Creates track log stats from commands log created by "history" cmd.

        Args:
            ctx (discord.ext.commands.context.Context): context (old commands)
        """

        ws_data_opts = {
            "Commands Log": False,
            "Track Log (Lifetime)": False,
            "Track Log (Year)": pd.DateOffset(years=1),
            "Track Log (Month)": pd.DateOffset(months=1),
            "Track Log (Week)": pd.DateOffset(weeks=1),
        }

        header = [
            "First time requested",
            "Last time requested",
            "Requests",
            "Title",
            "URL",
            "Duration",
            "Views",
            "Categories",
        ]
        columns_to_drop = header[:4]

        function_list = [
            ("First time requested", "min"),
            ("Last time requested", "max"),
            ("Requests", "count"),
        ]

        ws_names = tuple(ws_data_opts.keys())
        date_offsets = tuple(ws_data_opts.values())[1:]
        wss, ws_dfs = utils.get_worksheets("Discord Music Log", ws_names)
        ws_logs, ws_log_dfs = wss[1:], ws_dfs[1:]

        track_data = (ws_logs, ws_log_dfs, date_offsets)
        cmd_df = ws_dfs[0]
        cmd_df["Date"] = pd.to_datetime(cmd_df["Date"])  # ? try without convert to proper datetime type
        now = pd.Timestamp.now()

        for ws_log, ws_log_df, date_offset in zip(
            ws_logs, ws_log_dfs, date_offsets
        ):
            print(ws_log.title, "-----BEGINS-----")

            # create header if it's empty inside the worksheet
            if ws_log_df.empty:
                ws_log_df = pd.DataFrame(columns=header)

            # filter records according to timestamp that we got with date_offset
            if date_offset:
                timestamp = now - date_offset
                filter_ = cmd_df["Date"] >= timestamp
                filtered_cmd_df = cmd_df[filter_]
            else:
                filtered_cmd_df = cmd_df

            # groupby titles
            grouped_cmd_df = filtered_cmd_df.groupby(["URL", "Title"])["Date"]
            grouped_cmd_df = grouped_cmd_df.agg(function_list).reset_index()

            # merge with grouped cmd log with track log
            ws_log_df = ws_log_df.drop(labels=columns_to_drop, axis=1)  # ?
            merged_df = pd.merge(
                grouped_cmd_df, ws_log_df, on="URL", how="left"
            )
            merged_df = merged_df[header]

            # clean data
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
                        ) = await self.get_ytb_data_from_url(row.URL)
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

            utils.update_worksheet(ws_log, merged_df)

        await ctx.send("___Track logging updated up to this point.___")

        # IN NEXT COMMITS
        # TODO: use Track info tab and copy track info from there to other tabs
        # TODO: function at the end of this function to search for newly found songs
        # TODO: Commands Log, Track Info, User req count, Track Log (Lifetime, Year, Month, Week)

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
        # TODO: Why we have two play functions? Explain
        # TODO: Pylint, Documentation

        # making sure interaction timeout does not expire
        msg = "...Looking for song(s)... wait..."
        await interaction.response.send_message(msg)

        # voice channel check and connect
        vc = interaction.guild.voice_client
        if not vc:
            try:
                user_channel = interaction.user.voice.channel
            except AttributeError:
                msg = "Neither bot or you are connected to voice channel."
                await interaction.followup.send(msg)
                return

            await user_channel.connect()

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
            # print("SIGNAL FROM MUSIC.PY")
            player.next.set()
            # print("SIGNALED FROM MUSIC.PY")
        elif player.np_msg:
            player.view.update_msg()
            await player.update_player_status_message()

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

        descr = f"Jumped to {index}. song. "
        index -= 1

        if not vc.is_playing() and not vc.is_paused():
            player.next.set()
            print("SIGNAL FROM JUMP MUSIC.PY")
        else:
            index -= 1
            descr += "It will be played after current one finishes."

        player.next_pointer = index
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

    @app_commands.command(name="playlist")
    async def playlist(self, interaction, playlist_url: str):
        """Display all songs from a playlist to pick from."""

        # making sure interaction timeout does not expire
        await interaction.response.send_message(
            "...Looking for song(s)... wait..."
        )

        # get entries
        try:
            entries = await YTDLSource.create_source(
                interaction, playlist_url, loop=self.bot.loop, playlist=True
            )
        except youtube_dl.utils.DownloadError as err:
            await interaction.followup.send(err)
            return

        # load it into view
        player = self.get_player(interaction)
        view = SearchView(player, entries)
        player.view.update_msg()
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

        vc = interaction.guild.voice_client
        if player.loop_queue and not vc.is_playing() and not vc.is_paused():
            player.next_pointer = 0
            player.next.set()

    async def loop_track(self, interaction):
        player = self.get_player(interaction)
        player.toggle_loop_track()

        vc = interaction.guild.voice_client
        if player.loop_track and not vc.is_playing() and not vc.is_paused():
            player.next_pointer -= 1
            player.next.set()


async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        Music(bot), guilds=[discord.Object(id=os.environ["GUILD_ID"])]
    )

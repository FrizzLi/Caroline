import json
import os
import random
import re

import discord
import gspread
import pandas as pd
import pytz
import youtube_dl
from discord import app_commands
from discord.ext import commands

from cogs.music.player import MusicPlayer
from cogs.music.player_view import SearchView, get_readable_duration
from cogs.music.source import YTDLSource, ytdl


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

    # General commands
    def get_ytb_cmd_data(self, elem):
        search_expr = elem.content[6:]
        data = ytdl.extract_info(url=search_expr, download=False)
        if 'entries' in data:
            if len(data['entries']) == 1:  # for search single song
                data['title'] = data['entries'][0]['title']
                data['webpage_url'] = data['entries'][0]['webpage_url']

        timezone = pytz.timezone('Europe/Berlin')
        tz_aware_date = elem.created_at.astimezone(timezone)
        data['title'] = data['title'].replace('"',"'")
        data['webpage_url'] = data['webpage_url'].replace('"',"'")

        # only windows only uses hashtag # before H
        datetime = tz_aware_date.strftime("%Y-%m-%d %#H:%M:%S")
        author = elem.author.name
        title = data['title']
        webpage_url = data['webpage_url']
        # f"""=HYPERLINK("{data['webpage_url']}","{data['title']}")""",

        return datetime, author, title, webpage_url

    def get_ytb_track_data(self, row):
        data = ytdl.extract_info(url=row.URL, download=False)
        if 'entries' in data:
            if len(data['entries']) == 1:  # for search single song
                data['duration'] = data['entries'][0]['duration']
                data['view_count'] = data['entries'][0]['view_count']
                data['categories'] = data['entries'][0]['categories']

        duration = get_readable_duration(data['duration']) if 'duration' in data else ""
        views = f"{data['view_count']:,}" if 'view_count' in data else ""
        categories = ', '.join(data['categories']) if 'categories' in data else ""

        return duration, views, categories

    @commands.command()
    async def history(self, ctx, limit: int=1000):
        """Saves history of songs into Google Sheets."""

        table_data = []
        i = 0
        async for elem in ctx.channel.history(limit=limit):
            if elem.content.startswith("___") and (elem.author.name == 'GLaDOS' or elem.author.name == 'Caroline'):
                break
            i += 1

            # retrieve data from basic command - old bots (Groovy, Rhytm)
            if elem.content.lower()[1:].startswith("play"):
                try:
                    datetime, author, title, webpage_url = self.get_ytb_cmd_data(elem)
                except Exception as err:
                    print(f"{i}. Error: {err}. It is a playlist or there's other problem. command: {elem.content}")
                    continue

                rec = datetime, author, title, webpage_url
                table_data.append(rec)
                print(f"{i}. (old) downloaded: {rec}")

            # retrieve data from slash command - new bot (GLaDOS)
            elif (elem.author.name == 'GLaDOS' or elem.author.name == 'Caroline') and elem.embeds and elem.embeds[0].description.startswith('Queued'):
                msg = elem.embeds[0].description
                matching_expr = r"Queued \[(.+?)\]\((.+?)\) \[<@!?(\d+)>]"

                result = re.match(matching_expr, msg)
                if result:
                    title = result[1].replace('"',"'")
                    webpage_url = result[2].replace('"',"'")
                    author_id = result[3]
                author = await ctx.guild.fetch_member(author_id)
                tz_aware_date = elem.created_at.astimezone(pytz.timezone('Europe/Berlin'))
                datetime = tz_aware_date.strftime("%Y-%m-%d %#H:%M:%S")  # %Z%z

                rec = datetime, author.name, title, webpage_url
                table_data.append(rec)
                print(f"{i}. (new) downloaded: {rec}")

        # save to gsheets
        credentials_dict_string = os.environ.get("GOOGLE_CREDENTIALS")
        credentials_dict = json.loads(credentials_dict_string)  # TODO?
        g_credentials = gspread.service_account_from_dict(credentials_dict)
        g_sheet = g_credentials.open("Discord Music Log")
        g_work_sheet = g_sheet.worksheet("Commands Log")  # for creation sh.add_worksheet("Commands Log", df.shape[0], df.shape[1])
        df = pd.DataFrame(table_data, index=None)
        wks_formatted_rows = df.values.tolist()
        g_work_sheet.append_rows(wks_formatted_rows, value_input_option='USER_ENTERED')

        await ctx.send("___Messages saved up to this point.___")

    @commands.command()
    async def create_stats(self, ctx):
        """Saves history of songs into Google Sheets."""

        # get pandas format
        credentials_dict_string = os.environ.get("GOOGLE_CREDENTIALS")
        credentials_dict = json.loads(credentials_dict_string)
        g_credendials = gspread.service_account_from_dict(credentials_dict)
        g_sheet = g_credendials.open("Discord Music Log")
        cmd_wks = g_sheet.worksheet("Commands Log")
        cmd_df = pd.DataFrame(cmd_wks.get_all_records())
        cmd_df['Date'] = pd.to_datetime(cmd_df['Date'])
        now = pd.Timestamp.now()

        # preparation
        name_offset_dict = {
            "Track Log (Lifetime)": False,
            "Track Log (Year)": pd.DateOffset(years=1),
            "Track Log (3 Months)": pd.DateOffset(months=3),
            "Track Log (Month)": pd.DateOffset(months=1),
            "Track Log (Week)": pd.DateOffset(weeks=1)
        }

        for sheet_name, offset in name_offset_dict.items():
            print(sheet_name, "-----BEGINS-----")
            track_wks = g_sheet.worksheet(sheet_name)
            track_df = pd.DataFrame(track_wks.get_all_records())
            if track_df.empty:
                track_df = pd.DataFrame(columns=[
                    'First time requested', 'Last time requested',
                    'Requests', 'Title', 'URL',
                    'Duration', 'Views', 'Categories'
                ])

            # filter months
            if offset:
                timestamp = now - offset
                filter_ = cmd_df['Date'] >= timestamp
                filtered_cmd_df = cmd_df[filter_]
            else:
                filtered_cmd_df = cmd_df

            # groupby titles
            grouped_cmd_df = filtered_cmd_df.groupby(["URL", "Title"])["Date"]
            function_list = [("First time requested", "min"), ("Last time requested", "max"), ("Requests", "count")]
            grouped_cmd_df = grouped_cmd_df.agg(function_list).reset_index()

            # merge with track_df, rearrange, clean data
            track_df = track_df.drop(labels=["First time requested", "Last time requested", "Requests", "Title"], axis=1)
            merged_df = pd.merge(grouped_cmd_df, track_df, on='URL', how='left')
            merged_df = merged_df[[
                'First time requested', 'Last time requested',
                'Requests', 'Title', 'URL',
                'Duration', 'Views', 'Categories'
            ]]
            merged_df['First time requested'] = merged_df['First time requested'].astype(str)
            merged_df['Last time requested'] = merged_df['Last time requested'].astype(str)
            merged_df = merged_df.fillna(0)
            merged_df = merged_df.sort_values(by='Requests', ascending=False)

            # fill missing cells
            for i, row in enumerate(merged_df.itertuples(), 1):
                ytb_stats = row.Duration, row.Views, row.Categories
                if not all(ytb_stats):
                    try:
                        duration, views, categories = self.get_ytb_track_data(row)
                    except Exception as err:
                        print(f"{i}. error: {err}. (row: {row})")
                        continue

                    merged_df.at[row.Index, 'Duration'] = duration.replace(":", "︰")
                    merged_df.at[row.Index, 'Views'] = views
                    merged_df.at[row.Index, 'Categories'] = categories
                    print(f"Updated {i} row. ({duration}, {views}, {categories}) -- {row.Title}")

            # save to gsheets
            listed_table_result = [merged_df.columns.values.tolist()] + merged_df.values.tolist()  # first part is for header
            track_wks.update(listed_table_result, value_input_option='USER_ENTERED')  # value_input_option='USER_ENTERED' / 'RAW'

        await ctx.send("___Stats updated up to this point.___")

    # Slash commands, the main command
    @app_commands.command(name='play')
    async def _play(self, interaction, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search, retrieves a song and streams it.

        Args:
            search: str [Required]
                The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """

        await self.play(interaction, search)

    async def play(self, interaction, search):

        # making sure interaction timeout does not expire
        await interaction.response.send_message("...Looking for song(s)... wait...")

        # check if we're in channel, if not, join the one we are currently in
        vc = interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel
            await channel.connect()  # simplified cuz cannot invoke connect f.

        # If download is False, source will be a list of entries which will be used to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        try:
            entries = await YTDLSource.create_source(interaction, search, loop=self.bot.loop)
        except youtube_dl.utils.DownloadError as err:
            await interaction.followup.send(err)
            return

        player = self.get_player(interaction)
        send_signal = True if player.next_pointer >= len(player.queue) else False
        for entry in entries:
            source = {
                'webpage_url': entry['webpage_url'],
                'requester': interaction.user.name,
                'title': entry['title'],
            }
            player.queue.append(source)

        if send_signal:
            player.next.set()

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
    async def connect(self, interaction, *, channel: discord.VoiceChannel=None):
        """Connect to voice.
        This command also handles moving the bot to different channels.

        Args:
            channel: discord.VoiceChannel [Optional]
                The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
                will be made.
        """

        if channel is None:
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
            except TimeoutError:
                await interaction.response.send_message(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
                embed = discord.Embed(
                    description=f"Connected to channel: **{channel}**.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
            except TimeoutError:
                await interaction.response.send_message(f'Connecting to channel: <{channel}> timed out.')

    @app_commands.command()
    async def leave(self, interaction):
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
    @app_commands.command()
    async def jump(self, interaction, index: int):
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

    @app_commands.command()
    async def remove(self, interaction, index: int=None):
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
        if index-1 <= player.current_pointer:
            player.current_pointer -= 1

        embed = discord.Embed(
            description=f"Removed {index}. song [{s['title']}]({s['webpage_url']}).",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def clear(self, interaction):
        """Deletes entire queue of songs."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if not player.queue:
            return await interaction.response.send_message("There is no queue.")

        player.queue.clear()
        player.current_pointer = 0
        player.next_pointer = -1
        vc.stop()

        embed = discord.Embed(
            description="Queue has been cleared.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def seek(self, interaction, second: int=0):
        """Goes to a specific timestamp of currently played track."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.")

        player = self.get_player(interaction)
        if vc.is_paused() or not vc.is_playing():
            return await interaction.response.send_message("There is no song being played.")

        player.timestamp = second
        player.next_pointer -= 1
        vc.stop()

        embed = discord.Embed(
            description="Track has been seeked.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def search(self, interaction, search: str):
        """Searches 10 entries from query."""

        # making sure interaction timeout does not expire
        await interaction.response.send_message("...Looking for song(s)... wait...")

        # get entries
        try:
            entries = await YTDLSource.search_source(search, loop=self.bot.loop, download=False)
        except youtube_dl.utils.DownloadError as err:
            await interaction.followup.send(err)
            return

        # load it into view
        player = self.get_player(interaction)
        view = SearchView(player, entries)
        await interaction.channel.send(view.msg, view=view)

    @app_commands.command(name='playlist')
    async def playlist(self, interaction, search: str):
        """Display all songs from a playlist to pick from."""

        # making sure interaction timeout does not expire
        await interaction.response.send_message("...Looking for song(s)... wait...")

        # get entries
        try:
            entries = await YTDLSource.create_source(interaction, search, loop=self.bot.loop, playlist=True)
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
        """Randomizes the position of tracks in queue."""

        player = self.get_player(interaction)
        if not player.queue:
            return

        shuffled_remains = player.queue[player.current_pointer+1:]
        random.shuffle(shuffled_remains)

        player.queue = player.queue[:player.current_pointer+1] + shuffled_remains

    async def loop_queue(self, interaction):
        """Loops the queue of tracks."""

        player = self.get_player(interaction)
        player.loop_queue = not player.loop_queue

    async def loop_track(self, interaction):
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

# TODO: Code check: linting
